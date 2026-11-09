# Vendored frontend libraries

Served from here instead of a CDN, because camp sites can have poor connectivity
(SPEC §12). Copied from the npm packages, unchanged; the tarballs were checked
against the registry's sha512.

| Library | Version | Files |
|---|---|---|
| Bootstrap | 5.3.8 | `bootstrap/css/bootstrap.min.css`, `bootstrap/js/bootstrap.bundle.min.js` (with Popper) |
| Bootstrap Icons | 1.13.2 | `bootstrap-icons/bootstrap-icons.min.css`, `bootstrap-icons/fonts/` |
| HTMX | 2.0.11 | `htmx/htmx.min.js` |

To update one, download the new npm tarball, check its integrity hash, and replace
the same files. Update the version here too.
