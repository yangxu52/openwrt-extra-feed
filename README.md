# openwrt-foundry

OpenWrt package feed.

## Usage

Add this feed to `feeds.conf`:

```text
src-git foundry https://github.com/yangxu52/openwrt-foundry;openwrt-21.02
```

Update and install:

```sh
./scripts/feeds update foundry
./scripts/feeds install -a -p foundry
```

## Rust For 21.02

OpenWrt `21.02` Rust backport:

- `https://github.com/yangxu52/openwrt-rust-backports`

## License

This repository is distributed under `GPL-2.0-only`. See [LICENSE](LICENSE).
