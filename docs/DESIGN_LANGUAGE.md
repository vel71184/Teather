# Teather design language

Teather has more than one client — the Linux GTK desktop app today, other desktop
platforms and phone/receiver clients later — and they should feel like one
product. This document is how that consistency is achieved **without** a
cross-platform UI toolkit: each client is written natively for its platform and
follows the shared rules below. A framework that owns the UI (Electron, Flutter,
Compose Multiplatform, a single Qt client for every desktop) is explicitly
rejected here — see D-032 — because it works against "keep the Android side
lightweight" and "prefer a focused library over a framework that owns the
architecture" (`docs/DEVELOPMENT.md`).

The worst case this protects is deliberate: if sharing UI code ever stops being
worthwhile, we write the same small program again natively per platform, and it
still looks and behaves like Teather because it follows this spec.

## Principles

1. **Native widgets, native chrome.** Use the platform's real toolkit and its
   window/title conventions. Do not reskin the OS. Respect the user's system
   light/dark setting and system accent where the platform exposes one.
2. **One screen, grouped, scrollable.** No wizards, no tabs. A single vertically
   scrolling surface divided into labelled sections.
3. **The relay is the source of truth for state.** Every client renders the same
   state vocabulary the daemon / `RelayStatusWire` already emits — clients do not
   invent their own status names.
4. **Minimal bespoke styling.** The only place a client sets its own colour is the
   status pill (below) and the accent token. Everything else inherits the theme.

## Information architecture

Sections appear in this order on every client. A client omits a section it has no
controls for (the phone app has no "This phone" management section); it never
reorders them.

| Section | Desktop client | Android app |
|---|---|---|
| **Identity** | HeaderBar title "Teather" | bold "Teather relay" + one-line description |
| **Status** | pill + message + recovery hint + "closing does not disconnect" note | pill + monospace detail block |
| **Connection** | phone selector, Connect / Disconnect | upstream, SOCKS port, Start relay / Stop relay |
| **This phone** | Approve / Rename / Forget, auto-connect, phone-app install/update | — |
| **Sharing** | — | Copy laptop commands, Get the desktop client |
| **Preferences** | phone upstream, automatic failover, Appearance | Appearance |
| **Activity / Diagnostics** | counters + detail line (Diagnostics and a window restart live in the HeaderBar menu) | counters in the status block |

Terminology is shared: "upstream" (not "network"/"connection"), "Automatic
failover", "Appearance" (not "Theme"), "phone" for the Android device.

## Status pill

A pill is: a filled dot **●** in a semantic colour, the state word (capitalised,
taken verbatim from the daemon state or relay lifecycle), then an em-dash and a
short message.

```
● Connected — carrying traffic over cellular
● Disconnected — the phone is not attached
● Error — NetworkManager will not release teather0
```

Semantic colours (chosen to read on both light and dark backgrounds):

| Meaning | States | Light | Dark |
|---|---|---|---|
| OK | `connected`, relay `running` | `#1E7B34` | `#4CAF6A` |
| Working / standby | `connecting`, `detecting`, armed-but-idle | `#8A5A00` | `#E0A030` |
| Attention | `error`, `unavailable`, relay `failed` | `#B3261E` | `#E06B5C` |
| Neutral | `disconnected`, `detected`, `stopped`, starting | `#5F6368` | `#9AA0A6` |

The desktop client renders the pill as Pango markup on a label (no CSS provider,
so it cannot fight the GTK theme); because a markup colour is fixed rather than
theme-resolved, it uses the single dark-column value for each meaning, which is
legible on both light and dark GTK themes (`gui._STATUS_COLORS`). Android has
real `-night` resources, so it uses the light/dark pair and sets the `TextView`
colour directly.

## Palette tokens

Clients refer to these by name, not by hex. Only the accent and the pill colours
are Teather's own; everything else is the platform theme.

| Token | Light | Dark | Use |
|---|---|---|---|
| `accent` | `#5B3FD0` | `#9B84FF` | selection, suggested-action, links |
| `surface-sunken` | `#EEEAF8` | `#241E30` | the status/detail block background |
| pill OK / warn / err / neutral | see table above | | the status dot |

Android holds these in `res/values/colors.xml` + `res/values-night/colors.xml`;
the accent is wired into `Theme.Teather` as `android:colorAccent`. The GTK client
keeps the pill colours in `gui._STATUS_COLORS` and otherwise leans on the theme's
`suggested-action` / `destructive-action` / `dim-label` style classes.

## Typography

| Role | Size | Weight |
|---|---|---|
| Screen / window title | ~28sp / HeaderBar default | bold |
| Section heading | ~15sp / GTK `<b>` label | bold |
| Body | 14–16sp | regular |
| Status detail, counters | 13–14sp | monospace |

## Spacing

Base unit 8. Screen padding 20 horizontal / 24 top. Gap between sections 24, gap
between controls within a section 8–10.

## Iconography

A small set of symbolic icons with matching metaphors across clients. The desktop
client uses icon-theme symbolic names; Android uses bundled vector drawables when
it adds icons (text-only is acceptable until then).

| Concept | Symbolic name (GTK) |
|---|---|
| Connect / traffic | `network-transmit-receive-symbolic` |
| Disconnect | `network-offline-symbolic` |
| Approve | `emblem-ok-symbolic` |
| Rename | `document-edit-symbolic` |
| Forget | `user-trash-symbolic` |
| Phone app | `phone-symbolic` |
| Menu | `open-menu-symbolic` |

Icons are decorative: every control keeps its text label so a missing icon in an
unusual theme degrades cleanly.

## What stays platform-specific

Window chrome (HeaderBar vs. status/navigation bar colour), where the overflow
menu lives, dialog style (GTK `MessageDialog` vs. Android `AlertDialog` / toast),
and how the platform surfaces background state (tray indicator, notification).
These follow the platform, not this document.

## Non-goals

Custom-drawn widgets, a full theme override, animated transitions, or a bespoke
colour system beyond the tokens above. Teather is a utility; it should look like a
well-kept native settings panel, not a branded experience.
