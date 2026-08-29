#define _GNU_SOURCE

#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <linux/capability.h>
#include <linux/if.h>
#include <linux/if_tun.h>
#include <netinet/in.h>
#include <pwd.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef TEATHER_TUNNEL_PATH
#define TEATHER_TUNNEL_PATH "/usr/lib/teather/tun2proxy"
#endif

#define INTERFACE_NAME "teather0"
#define IP_PATH "/usr/sbin/ip"

extern unsigned int if_nametoindex(const char *ifname);

static char *const safe_env[] = { "PATH=/usr/sbin:/usr/bin:/sbin:/bin", "RUST_LOG=off", NULL };

static void fail(const char *message) {
    fprintf(stderr, "teather-helper: %s\n", message);
    exit(1);
}

static long parse_number(const char *value, long minimum, long maximum, const char *message) {
    char *end = NULL;
    errno = 0;
    long result = strtol(value, &end, 10);
    if (errno || !end || *end || result < minimum || result > maximum) fail(message);
    return result;
}

static int run_command(char *const arguments[]) {
    pid_t child = fork();
    if (child < 0) fail("cannot fork network command");
    if (child == 0) {
        execve(IP_PATH, arguments, safe_env);
        _exit(127);
    }
    int status = 0;
    while (waitpid(child, &status, 0) < 0) {
        if (errno != EINTR) fail("cannot wait for network command");
    }
    return WIFEXITED(status) ? WEXITSTATUS(status) : 128;
}

static char *capture_ip(char *const arguments[]) {
    int descriptors[2];
    if (pipe2(descriptors, O_CLOEXEC) != 0) fail("cannot inspect network state");
    pid_t child = fork();
    if (child < 0) fail("cannot fork network inspection");
    if (child == 0) {
        close(descriptors[0]);
        if (dup2(descriptors[1], STDOUT_FILENO) < 0) _exit(127);
        close(descriptors[1]);
        execve(IP_PATH, arguments, safe_env);
        _exit(127);
    }
    close(descriptors[1]);
    size_t capacity = 16384;
    size_t length = 0;
    char *result = calloc(capacity, 1);
    if (!result) fail("out of memory during network inspection");
    while (length + 1 < capacity) {
        ssize_t count = read(descriptors[0], result + length, capacity - length - 1);
        if (count == 0) break;
        if (count < 0) {
            if (errno == EINTR) continue;
            free(result);
            fail("cannot read network inspection");
        }
        length += (size_t)count;
    }
    if (length + 1 >= capacity) {
        close(descriptors[0]);
        free(result);
        fail("network inspection output is too large");
    }
    close(descriptors[0]);
    int status = 0;
    while (waitpid(child, &status, 0) < 0 && errno == EINTR) {}
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        free(result);
        fail("network inspection command failed");
    }
    result[length] = '\0';
    return result;
}

static bool vpn_interface(const char *line) {
    const char *device = strstr(line, " dev ");
    if (!device) return false;
    device += 5;
    return strncmp(device, "tun", 3) == 0 || strncmp(device, "tap", 3) == 0 ||
        strncmp(device, "wg", 2) == 0 || strncmp(device, "vpn", 3) == 0 ||
        strncmp(device, "tailscale", 9) == 0 || strncmp(device, "proton", 6) == 0;
}

static bool physical_interface(const char *line) {
    const char *device = strstr(line, " dev ");
    if (!device) return false;
    device += 5;
    size_t length = strcspn(device, " \t");
    if (length == 0 || length >= IFNAMSIZ) return false;
    char name[IFNAMSIZ];
    memcpy(name, device, length);
    name[length] = '\0';
    char path[128];
    snprintf(path, sizeof(path), "/sys/class/net/%s/device", name);
    return access(path, F_OK) == 0;
}

static const char *route_destination_token(const char *line, size_t *length) {
    const char *destination_start = line;
    *length = strcspn(destination_start, " \t");
    static const char *const route_types[] = {
        "unicast", "local", "broadcast", "multicast", "throw", "unreachable",
        "prohibit", "blackhole", "nat", "xresolve",
    };
    for (size_t index = 0; index < sizeof(route_types) / sizeof(route_types[0]); index++) {
        size_t type_length = strlen(route_types[index]);
        if (*length == type_length && strncmp(destination_start, route_types[index], *length) == 0) {
            destination_start += *length;
            while (*destination_start == ' ' || *destination_start == '\t') destination_start++;
            *length = strcspn(destination_start, " \t");
            break;
        }
    }
    return destination_start;
}

static bool route_has_destination(const char *line, const char *expected) {
    size_t length = 0;
    const char *destination = route_destination_token(line, &length);
    size_t expected_length = strlen(expected);
    return length == expected_length && strncmp(destination, expected, length) == 0;
}

static bool route_overlaps_virtual_pool(const char *line) {
    size_t length = 0;
    const char *destination_start = route_destination_token(line, &length);
    if (length == 0 || length >= 64 || route_has_destination(line, "default"))
        return false;
    char destination[64];
    memcpy(destination, destination_start, length);
    destination[length] = '\0';
    char *slash = strchr(destination, '/');
    long prefix = 32;
    if (slash) {
        *slash = '\0';
        prefix = parse_number(slash + 1, 0, 32, "invalid IPv4 route prefix");
    }
    struct in_addr parsed;
    if (inet_pton(AF_INET, destination, &parsed) != 1) fail("invalid IPv4 route destination");
    unsigned int common = (unsigned int)(prefix < 15 ? prefix : 15);
    uint32_t mask = common == 0 ? 0 : UINT32_MAX << (32 - common);
    uint32_t network = ntohl(parsed.s_addr);
    uint32_t pool = (198U << 24) | (18U << 16);
    return (network & mask) == (pool & mask);
}

static bool standard_policy_rule(const char *line) {
    char *end = NULL;
    errno = 0;
    long priority = strtol(line, &end, 10);
    if (errno || end == line || *end != ':') return false;
    char from[8], source[8], operation[8], table[16], extra;
    int fields = sscanf(end + 1, "%7s %7s %7s %15s %c", from, source, operation, table, &extra);
    if (fields != 4 || strcmp(from, "from") != 0 || strcmp(source, "all") != 0 ||
        strcmp(operation, "lookup") != 0)
        return false;
    bool table_matches =
        (priority == 0 && strcmp(table, "local") == 0) ||
        (priority == 32766 && strcmp(table, "main") == 0) ||
        (priority == 32767 && strcmp(table, "default") == 0);
    return table_matches;
}

static void validate_network_state(void) {
    if (if_nametoindex(INTERFACE_NAME) != 0) fail("teather0 already exists; refusing ambiguous ownership");
    char *route_args[] = { IP_PATH, "-4", "-o", "route", "show", "table", "all", NULL };
    char *routes = capture_ip(route_args);
    bool found_default = false;
    char *save = NULL;
    for (char *line = strtok_r(routes, "\n", &save); line; line = strtok_r(NULL, "\n", &save)) {
        if (strstr(line, " dev teather0") || route_overlaps_virtual_pool(line))
            fail("Teather route collision detected");
        if (route_has_destination(line, "0.0.0.0/1") ||
            route_has_destination(line, "128.0.0.0/1"))
            fail("split-default policy is ambiguous");
        if (strncmp(line, "default ", 8) == 0) {
            found_default = true;
            if (vpn_interface(line)) fail("VPN-like default route is active");
            if (!physical_interface(line)) fail("default route is not attached to a physical interface");
            char *metric = strstr(line, " metric ");
            if (metric) {
                char *end = NULL;
                errno = 0;
                long value = strtol(metric + 8, &end, 10);
                if (errno || end == metric + 8 || value < 0 || value > 1000000)
                    fail("invalid route metric");
                if (value >= 32000) fail("existing default would not remain preferred");
            }
        }
    }
    free(routes);
    if (!found_default) fail("no existing IPv4 default route");

    char *rule_args[] = { IP_PATH, "-4", "-o", "rule", "show", NULL };
    char *rules = capture_ip(rule_args);
    save = NULL;
    for (char *line = strtok_r(rules, "\n", &save); line; line = strtok_r(NULL, "\n", &save))
        if (!standard_policy_rule(line)) fail("nonstandard IPv4 policy routing is active");
    free(rules);

    char *address_args[] = { IP_PATH, "-4", "-o", "address", "show", NULL };
    char *addresses = capture_ip(address_args);
    if (strstr(addresses, " 192.0.2.1/")) fail("192.0.2.1 address collision detected");
    free(addresses);
}

static void validate_proxy(int port) {
    int socket_fd = socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (socket_fd < 0) fail("cannot validate loopback proxy");
    struct sockaddr_in address = {
        .sin_family = AF_INET,
        .sin_port = htons((uint16_t)port),
        .sin_addr.s_addr = htonl(INADDR_LOOPBACK),
    };
    if (connect(socket_fd, (struct sockaddr *)&address, sizeof(address)) != 0) {
        close(socket_fd);
        fail("loopback proxy port is not listening");
    }
    close(socket_fd);
}

static int open_tun(void) {
    int descriptor = open("/dev/net/tun", O_RDWR | O_CLOEXEC | O_NOCTTY);
    if (descriptor < 0) fail("cannot open /dev/net/tun");
    struct ifreq request;
    memset(&request, 0, sizeof(request));
    request.ifr_flags = IFF_TUN | IFF_NO_PI;
    strncpy(request.ifr_name, INTERFACE_NAME, IFNAMSIZ - 1);
    if (ioctl(descriptor, TUNSETIFF, &request) != 0) {
        close(descriptor);
        fail("cannot create teather0");
    }
    if (strcmp(request.ifr_name, INTERFACE_NAME) != 0) {
        close(descriptor);
        fail("kernel returned unexpected interface name");
    }
    return descriptor;
}

static void configure_tun(void) {
    char *address[] = { IP_PATH, "address", "add", "192.0.2.1/32", "dev", INTERFACE_NAME, NULL };
    char *link[] = { IP_PATH, "link", "set", "dev", INTERFACE_NAME, "mtu", "1500", "up", NULL };
    char *dns_route[] = { IP_PATH, "route", "add", "198.18.0.0/15", "dev", INTERFACE_NAME, NULL };
    char *default_route[] = { IP_PATH, "route", "add", "default", "dev", INTERFACE_NAME, "metric", "32000", NULL };
    if (run_command(address) || run_command(link) || run_command(dns_route) || run_command(default_route))
        fail("failed to configure bounded Teather interface state");
}

static void validate_tunnel_binary(void) {
    struct stat info;
    if (lstat(TEATHER_TUNNEL_PATH, &info) != 0 || !S_ISREG(info.st_mode) || info.st_uid != 0 ||
        (info.st_mode & (S_IWGRP | S_IWOTH)))
        fail("tunnel binary has unsafe owner or mode");
}

static void drop_privileges(uid_t uid, gid_t gid) {
    for (int capability = 0; capability <= CAP_LAST_CAP; capability++)
        if (prctl(PR_CAPBSET_DROP, capability, 0, 0, 0) != 0 && errno != EINVAL)
            fail("cannot drop capability bounding set");
    if (setgroups(0, NULL) != 0) fail("cannot drop supplementary groups");
    if (setgid(gid) != 0 || setuid(uid) != 0) fail("cannot drop uid/gid");
    struct __user_cap_header_struct header = { _LINUX_CAPABILITY_VERSION_3, 0 };
    struct __user_cap_data_struct data[2] = {0};
    if (syscall(SYS_capset, &header, data) != 0) fail("cannot clear capabilities");
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0) fail("cannot lock privilege state");
}

int main(int argc, char **argv) {
    if (argc != 3 || strcmp(argv[1], "run") != 0) fail("expected exactly: run LOOPBACK_PORT");
    if (geteuid() != 0) fail("must be invoked through the Teather polkit action");
    const char *uid_text = getenv("PKEXEC_UID");
    if (!uid_text) fail("PKEXEC_UID is required");
    uid_t uid = (uid_t)parse_number(uid_text, 1, 2147483647L, "invalid PKEXEC_UID");
    struct passwd *account = getpwuid(uid);
    if (!account || account->pw_uid != uid || account->pw_gid == 0) fail("invalid desktop account");
    int port = (int)parse_number(argv[2], 1024, 65535, "invalid loopback proxy port");
    pid_t parent = getppid();
    if (prctl(PR_SET_PDEATHSIG, SIGTERM, 0, 0, 0) != 0) fail("cannot set parent-death handling");
    if (getppid() != parent || parent == 1) fail("invoking daemon exited");

    clearenv();
    validate_tunnel_binary();
    validate_network_state();
    validate_proxy(port);
    int tun_fd = open_tun();
    configure_tun();
    if (fcntl(tun_fd, F_SETFD, 0) != 0) {
        close(tun_fd);
        fail("cannot inherit TUN descriptor");
    }
    drop_privileges(uid, account->pw_gid);
    if (prctl(PR_SET_PDEATHSIG, SIGTERM, 0, 0, 0) != 0 || getppid() != parent)
        fail("cannot preserve parent-death handling after privilege drop");

    char port_text[6], descriptor_text[16], proxy[64];
    snprintf(port_text, sizeof(port_text), "%d", port);
    snprintf(descriptor_text, sizeof(descriptor_text), "%d", tun_fd);
    snprintf(proxy, sizeof(proxy), "socks5://127.0.0.1:%s", port_text);
    char *const tunnel_arguments[] = {
        TEATHER_TUNNEL_PATH,
        "--proxy", proxy,
        "--tun-fd", descriptor_text,
        "--close-fd-on-drop", "true",
        "--dns", "virtual",
        "--virtual-dns-pool", "198.18.0.0/16",
        "--mtu", "1500",
        "--tcp-timeout", "300",
        "--max-sessions", "64",
        "--verbosity", "off",
        "--exit-on-fatal-error",
        NULL,
    };
    execve(TEATHER_TUNNEL_PATH, tunnel_arguments, safe_env);
    close(tun_fd);
    fail("cannot execute pinned tunnel binary");
    return 1;
}
