# BV-05 versions and source pins

| Item | Recorded version or revision | Evidence |
| --- | --- | --- |
| Host | macOS 26.5.1 (25F80), arm64 | `sw_vers` and `uname -m`, exit 0 |
| Docker Sandboxes CLI | v0.45.1, `9d79d90ee4c5d297fb3d36b75384e8cea7a4fbcb` | `sbx version`, exit 0 |
| Imported design | `8384ca71d1ecc8ff590878fc4351954dbadd06d4` | [BV-05](../../research/imported/design-wiki-8384ca7/backend-validation-spikes.md#bv-05-sbx-kit-routing-and-server-trust) and [authentication](../../research/imported/design-wiki-8384ca7/spiffe-mtls-authentication.md) |
| Docker documentation | `dvdksn/docs@75d1ee312280c2028be294e043edeaf35f2fe1bb` | Read pinned [kit reference](https://github.com/dvdksn/docs/blob/75d1ee312280c2028be294e043edeaf35f2fe1bb/content/manuals/ai/sandboxes/customize/kit-reference.md), [kit example](https://github.com/dvdksn/docs/blob/75d1ee312280c2028be294e043edeaf35f2fe1bb/content/manuals/ai/sandboxes/customize/kit-examples.md), [credentials](https://github.com/dvdksn/docs/blob/75d1ee312280c2028be294e043edeaf35f2fe1bb/content/manuals/ai/sandboxes/configuration/credentials.md), [host services](https://github.com/dvdksn/docs/blob/75d1ee312280c2028be294e043edeaf35f2fe1bb/content/manuals/ai/sandboxes/workflows/development.md), and [troubleshooting](https://github.com/dvdksn/docs/blob/75d1ee312280c2028be294e043edeaf35f2fe1bb/content/manuals/ai/sandboxes/troubleshooting.md) through GitHub REST |
| Docker kit schema | Version 2 is documented for sbx 0.36 and later | Pinned kit reference, lines 34 to 42 |
| Harness | No harness run | Fixture remains unexecuted |

The sbx source was unavailable from the public release repository. The CLI revision above identifies the installed binary, not a reviewed source checkout. No dependency source was cloned. Pinned documentation was read through GitHub REST, and the local checkout was `c7b0fa9c17cbf255986b20863ac93d9bf2de717e` before this work.
