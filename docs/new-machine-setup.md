# Setting up a new machine

Bootstrapping this project on a fresh macOS laptop, and the equivalent shape for
a remote host. Steps 1–3 necessarily happen before the repo exists, so read them
from the web copy rather than from a clone.

Nothing in `data/` is version-controlled and none of it needs to be carried
between machines — every input is staged on demand from calculon.

## macOS laptop

```bash
# 1. Toolchain
xcode-select --install

# 2. Miniconda for Apple silicon
curl -fsSLo /tmp/miniconda.sh \
  https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh
bash /tmp/miniconda.sh -b -p "$HOME/miniconda3"
"$HOME/miniconda3/bin/conda" init zsh && exec zsh

# 3. Clone
mkdir -p ~/Documents/GitHub && cd ~/Documents/GitHub
git clone https://github.com/i4Ds/solar-burst-multiview.git
cd solar-burst-multiview

# 4. Environment
conda env create -f environment.yml
conda activate solar-burst-multiview

# 5. Calculon access, then verify it works
scp <olduser>@<oldhost>.local:~/.ssh/id_ed25519 ~/.ssh/
chmod 600 ~/.ssh/id_ed25519
ssh -i ~/.ssh/id_ed25519 andre_csillaghy@calculon.informatik.fhnw.ch hostname
```

Copying the existing SSH key is preferable to generating a new one, which would
have to be re-registered with FHNW. AirDrop works equally well if Remote Login
is not enabled on the old machine.

Apple's Migration Assistant is the alternative to steps 1–5 and brings across the
conda install, the SSH key and the Zotero data directory in one move. Prefer a
clean setup when the old disk is close to full.

## Verifying the install

```bash
python -c "import astropy, sunpy, numpy; print('core OK')"
python -c "import casacore.tables; print('casacore OK')"   # see caveat below
ssh -i ~/.ssh/id_ed25519 andre_csillaghy@calculon.informatik.fhnw.ch \
  'ls /mnt/nas05/data02/rohit | head'
```

**Caveat:** `environment.yml` does not yet declare `python-casacore`,
`reproject`, `scipy`, `pyyaml` or `tqdm`, so the casacore check fails on a fresh
environment. Adding them is the first task of Phase 0 in
[`reproduction-plan.md`](reproduction-plan.md); `python-casacore` 3.8.1 is
available on conda-forge for osx-arm64 and needs no compilation.

## Zotero

The reference library syncs through zotero.org with attachment storage on WebDAV,
so signing in on a new machine restores both metadata and PDFs. The local data
directory (`~/Zotero`) does not need copying. Two passwords are required, the
zotero.org account and the WebDAV endpoint, and both typically live only in the
old machine's keychain — retrieve them before decommissioning it, and trigger one
final sync.

## Remote hosts

Calculon, and later CSCS, follow the same shape with one difference: the heavy
radio-astronomy tools are needed there, and calculon currently has none of them,
nor any container runtime. See §2 and Phase 3 of
[`reproduction-plan.md`](reproduction-plan.md) for what has to be built and the
preference for Apptainer over compiling from source.

Conda is also absent on calculon, so a user-space micromamba is the starting
point:

```bash
curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
./bin/micromamba create -n solarburst -c conda-forge python=3.10 python-casacore numpy astropy
```

Stage work under `/scratch` or `/data`, both of which have ample free space, and
treat `/mnt/nas05/data02/rohit` as strictly read-only.
