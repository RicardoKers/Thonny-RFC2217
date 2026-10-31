# Third-party notices

The source files in this repository retain their original licenses. The root MIT license does not replace separate licenses attached to included components.

| Component | License / retained notices |
|---|---|
| Thonny | MIT, [thonny/LICENSE.txt](thonny/LICENSE.txt) |
| Minny | MIT, [minny/LICENSE](minny/LICENSE) |
| Thonny dependencies and icons | Preserve [thonny/licenses/](thonny/licenses/), including Eclipse icon notices and applicable licenses |
| Vendored type stubs | Preserve the licenses and copyright notices inside [thonny/thonny/vendored_libs/](thonny/thonny/vendored_libs/) |
| PySerial | BSD-3-Clause; installed through the declared dependencies and included with its license when bundled |
| CPython, Tcl/Tk, Basedpyright, Node.js and other runtime dependencies | Retain the licenses distributed with the corresponding binary packages when producing Windows installers or portable archives |

The development virtual environment, local application profile, caches, and raw machine logs are intentionally excluded from the source repository. Windows release packaging must collect the licenses of the actual installed runtime distributions in addition to the upstream source notices listed above.

