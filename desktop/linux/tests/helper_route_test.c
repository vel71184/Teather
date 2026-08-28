#define main teather_helper_program_main
#include "../helper/teather-helper.c"
#undef main

#include <stdio.h>

static int check(bool condition, const char *message) {
    if (condition) return 0;
    fprintf(stderr, "helper route test failed: %s\n", message);
    return 1;
}

int main(void) {
    int failed = 0;
    failed |= check(!route_overlaps_virtual_pool("default via 10.0.2.2 dev eth0 metric 100"),
        "default route must not be parsed as an address");
    failed |= check(!route_overlaps_virtual_pool("local 127.0.0.1 dev lo table local scope host"),
        "local-table route type must be accepted");
    failed |= check(!route_overlaps_virtual_pool("broadcast 10.0.2.255 dev eth0 table local"),
        "broadcast route type must be accepted");
    failed |= check(!route_overlaps_virtual_pool("10.0.2.0/24 dev eth0 scope link"),
        "unrelated unicast route must not collide");
    failed |= check(route_overlaps_virtual_pool("198.18.0.0/15 dev eth0"),
        "exact virtual pool must collide");
    failed |= check(route_overlaps_virtual_pool("local 198.19.2.3 dev lo table local"),
        "typed host route inside virtual pool must collide");
    failed |= check(route_overlaps_virtual_pool("blackhole 198.18.0.0/16"),
        "typed prefix inside virtual pool must collide");
    failed |= check(route_overlaps_virtual_pool("198.0.0.0/8 dev eth0"),
        "covering prefix must collide");
    failed |= check(!route_overlaps_virtual_pool("198.20.0.0/16 dev eth0"),
        "adjacent prefix must not collide");
    failed |= check(route_has_destination("0.0.0.0/1 dev eth0", "0.0.0.0/1"),
        "lower split-default destination must match exactly");
    failed |= check(route_has_destination("unicast 128.0.0.0/1 dev eth0", "128.0.0.0/1"),
        "typed upper split-default destination must match exactly");
    failed |= check(!route_has_destination("0.0.0.0/10 dev eth0", "0.0.0.0/1"),
        "split-default comparison must not accept a prefix substring");
    failed |= check(standard_policy_rule("0:\tfrom all lookup local"),
        "tab-separated local rule must be accepted");
    failed |= check(standard_policy_rule("32766: from all lookup main"),
        "space-separated main rule must be accepted");
    failed |= check(standard_policy_rule("32767:\tfrom all lookup default"),
        "tab-separated default rule must be accepted");
    failed |= check(!standard_policy_rule("1000:\tfrom all lookup 100"),
        "nonstandard table must be refused");
    failed |= check(!standard_policy_rule("32766:\tfrom all lookup main suppress_prefixlength 0"),
        "rule attributes must be refused");
    return failed;
}
