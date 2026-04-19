# SPDX-License-Identifier: GPL-2.0-only

include $(TOPDIR)/rules.mk

PKG_NAME:=veex
PKG_VERSION:=0.7.0
PKG_RELEASE:=1

VEEX_REPO_OWNER:=Project-VeeX
VEEX_REPO_NAME:=VeeX

# GitHub codeload archives unpack to "$(repo)-$(version)".
PKG_BUILD_DIR:=$(BUILD_DIR)/$(VEEX_REPO_NAME)-$(PKG_VERSION)

# v0.7.0 tag resolves to commit b3e1734d84cb4420c2d134e8de05fa8223ca37ab.
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION).tar.gz
PKG_SOURCE_URL:=https://codeload.github.com/$(VEEX_REPO_OWNER)/$(VEEX_REPO_NAME)/tar.gz/v$(PKG_VERSION)?
PKG_HASH:=d534b3eaf95d6d446d51d21ded66170e2fd8ae0df7546825b8e507679821c4ad

PKG_MAINTAINER:=openwrt-foundry maintainers
PKG_LICENSE:=MPL-2.0
PKG_LICENSE_FILES:=LICENSE

PKG_BUILD_DEPENDS:=rust/host
PKG_BUILD_PARALLEL:=1

# Current upstream binary crate: crates/cli -> [[bin]] name = "veex".
MAKE_PATH:=crates/cli

# Keep the package thin even if upstream later exposes more binaries.
VEEX_CARGO_INSTALL_ARGS:=--bin veex

include $(INCLUDE_DIR)/package.mk
include $(TOPDIR)/feeds/packages/lang/rust/rust-package.mk

define Package/veex
  SECTION:=net
  CATEGORY:=Network
  SUBMENU:=Web Servers/Proxies
  TITLE:=VeeX CLI
  URL:=https://github.com/$(VEEX_REPO_OWNER)/$(VEEX_REPO_NAME)
  DEPENDS:=$(RUST_ARCH_DEPENDS)
endef

define Package/veex/description
 VeeX thin OpenWrt package. Installs only /usr/bin/veex.
endef

Build/Compile=$(call Build/Compile/Cargo,,$(VEEX_CARGO_INSTALL_ARGS))

define Package/veex/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_INSTALL_DIR)/bin/veex $(1)/usr/bin/
endef

$(eval $(call BuildPackage,veex))
