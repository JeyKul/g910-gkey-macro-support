# Arch Linux installation (development branch)

Run as your regular desktop user:

```sh
sudo pacman -S --needed base-devel git
git clone --branch dev https://github.com/JeyKul/g910-gkey-macro-support.git
cd g910-gkey-macro-support
bash install-arch -n
```

If already cloned, switch to `dev` and pull before running the helper.
The helper builds the remote `dev` branch, not uncommitted local changes.
It uses makepkg/pacman, not pip, and installs the application globally.
Review the PKGBUILD before building. Dependency installation and package installation may ask for sudo.

Unplug/reconnect the keyboard, then start the user service:

```sh
systemctl --user enable --now g910-gkeys.service
journalctl --user -u g910-gkeys.service -b -n 80 --no-pager
```

Your configuration is `~/.config/g910-gkeys/config.json`; an existing file is preserved.
The default is installed at `/etc/g910-gkeys/config.json`.
The generic `./install` is unchanged; use `bash install-arch` on Arch.
Omit `-n` to enable/start the service automatically.

If a previous manual installation created a user service override, inspect it with
`systemctl --user cat g910-gkeys.service` before testing. Likewise inspect any old
`/etc/udev/rules.d/60-g910-gkeys.rules`, which takes precedence over the packaged rule.
This installer does not delete existing overrides or previous pip installations.

Remove the package:

```sh
systemctl --user disable --now g910-gkeys.service
sudo pacman -R g910-gkeys-git
```

The user configuration is retained. Hardware operation must be tested on a real keyboard.
