# Source provenance

This repository is an unofficial source snapshot combining Thonny, Minny, and the RFC 2217 development harness. The upstream source trees are included as ordinary directories, without nested Git repositories. Their license and attribution files are preserved.

| Component | Upstream | Base version | Upstream base commit | Local source revision included |
|---|---|---|---|---|
| Thonny | https://github.com/thonny/thonny | 6.0.0.dev1 | `99de9cfe057a79d40da674e5c319e4b0142f9579` | `5781c463e3b8718e29198f303431a8e502342929` |
| Minny | https://github.com/aivarannamaa/minny | 0.0.1a2 | `4471205b1d8f905dd410a4b35c6037686d6917ab` | `ebc4192db572390a927b74ab34f72f7a6c25ee8d` |

The local revision identifiers describe the development checkouts from which this snapshot was exported. They are not claims that these commits exist in the upstream repositories. `SOURCE_MANIFEST.json` records the exported revisions and tracked-file counts.

The local changes consist of RFC 2217 transport support and tests in Minny; a connection option and persistence in Thonny; the I/O bridge and deferred configuration fixes required by the current development versions; and language-server process lifecycle/workspace fixes discovered during Windows validation. No upstream pull request or proposal is implied by publication of this snapshot.

Source validation was performed on Windows with CPython 3.11.9, Tk 8.6 and PySerial 3.5. The exact installed development dependency versions are recorded in `requirements-tested.txt`. The distribution version `0.1.0` is separate from the upstream Thonny version.

No SimNodus source or MicroPython firmware is included or modified by this repository. SimNodus is an external integration-test target.

