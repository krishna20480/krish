#!/bin/bash

# Wallet and pool info
WALLET="44Dzqvm7mx3LTETpwC5xRDQQs9Mn3Y1ZSV3YkJdQSDUaTo7xXMirqtnUu3ZtoYky2CE4gMJDKJPivUSRvNAvqBawJ8agMuU"
POOL="pool.supportxmr.com:3333"
WORKER="${1:-MacM2Rig}"  # Default worker name

echo "[+] Installing Homebrew packages if missing..."
# Install Homebrew if not installed
which brew >/dev/null 2>&1 || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Ensure dependencies are present
brew install cmake automake autoconf libtool pkg-config hwloc openssl git

echo "[+] Cloning XMRig..."
cd ~
rm -rf xmrig
git clone https://github.com/xmrig/xmrig.git
cd xmrig

echo "[+] Building XMRig for macOS ARM64..."
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DOPENSSL_ROOT_DIR=$(brew --prefix openssl)
make -j$(sysctl -n hw.ncpu)

echo "[+] Starting miner in 5 seconds..."
sleep 5

./xmrig -o $POOL -u $WALLET -p $WORKER -k --coin monero
