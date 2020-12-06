#!/usr/bin/env python3

import yaml
from pathlib import Path
from shutil import rmtree
import sys
from subprocess import run
from os import getenv

profile_folder = Path(getenv("PROFILES", "./profiles"))


def die(msg: str):
    """Quit script with error message

    msg (str): Error message to print
    """
    print(msg)
    quit(1)


def usage(code: int = 0):
    """Print script usage

    Args:
        code (int): exit code
    """
    print(
        f"""Usage: {sys.argv[0]} <profile> [options...]

    clean           Cleanup feeds related parts in the tree and exit.
    list            List available profiles"""
    )
    quit(code)

def load_yaml(fname: str, profile: dict):
    profile_file = (profile_folder / fname).with_suffix(".yml")

    if not profile_file.is_file():
        die(f"Profile {fname} not found")

    new = yaml.safe_load(profile_file.read_text())
    for n in new:
        if n in {"profile", "target", "subtarget", "external_target"}:
            if profile.get(n):
                die(f"Duplicate tag found {n}")
            profile.update({n:new.get(n)})
        elif n in {"description"}:
            profile["description"].append(new.get(n))
        elif n in {"packages"}:
            profile["packages"].extend(new.get(n))
        elif n in {"diffconfig"}:
            profile["diffconfig"] += new.get(n)
        elif n in {"feeds"}:
            for f in new.get(n):
                if f.get("name", "") == "" or f.get("uri", "") == "":
                     die(f"Found bad feed {f}")
                profile["feeds"][f.get("name")] = f
    return profile

if "list" in sys.argv:
    print(f"Profiles in {profile_folder}")

    print("\n".join(map(lambda p: str(p.stem), profile_folder.glob("*.yml"))))
    quit(0)

if "help" in sys.argv:
    usage()

if len(sys.argv) < 2:
    usage(1)

rmtree("./tmp", ignore_errors=True)
rmtree("./packages/feeds/", ignore_errors=True)
rmtree("./feeds", ignore_errors=True)
rmtree("./tmp", ignore_errors=True)
if Path("./feeds.conf").is_file():
    Path("./feeds.conf").unlink()
if Path("./.config").is_file():
    Path("./.config").unlink()

if "clean" in sys.argv:
    print("Tree is now clean")
    quit(0)

profile = {"packages":[], "description": [],"diffconfig":"", "feeds":{}}

for p in sys.argv[1:]:
    profile = load_yaml(p, profile)

# print(yaml.dump(profile))

for d in profile.get("description"):
    print(d)

feeds_conf = Path("feeds.conf")
if feeds_conf.is_file():
    feeds_conf.unlink()

feeds = []

with open("feeds.conf.default", "r") as default_feeds:
    for line in default_feeds:
        feed = line.rstrip()
        print(f"Adding default feed '{feed}'")
        feeds.append(feed.replace(" ", ","))

for p in profile.get("feeds", []):
    try:
        f = profile["feeds"].get(p)
        if not "revision" in f:
            die(f"Please specify revision for the following feed: {f}")
        feeds.append(
            f'{f.get("method", "src-git")},{f["name"]},{f["uri"]}^{f.get("revision")}'
        )
    except:
        print(f"Badly configured feed: {f}")

if run(["./scripts/feeds", "setup", *feeds]).returncode:
    die(f"Error setting up feeds")

if run(["./scripts/feeds", "update"]).returncode:
    die(f"Error updating feeds")

for p in profile.get("feeds", []):
    f = profile["feeds"].get(p)
    if run(["./scripts/feeds", "install", "-a", "-f", "-p", f.get("name")]).returncode:
        die(f"Error installing {feed}")

if profile.get("external_target", False):
    if run(["./scripts/feeds", "install", profile["target"]]).returncode:
        die(f"Error installing external target {profile['target']}")

config_output = f"""CONFIG_TARGET_{profile["target"]}=y
CONFIG_TARGET_{profile["target"]}_{profile["subtarget"]}=y
CONFIG_TARGET_{profile["target"]}_{profile["subtarget"]}_DEVICE_{profile["profile"]}=y
"""

config_output += f"{profile.get('diffconfig', '')}"

for package in profile.get("packages", []):
    print(f"Add package to .config: {package}")
    config_output += f"CONFIG_PACKAGE_{package}=y\n"

Path(".config").write_text(config_output)
print("Configuration written to .config")

rmtree("./tmp", ignore_errors=True)
print("Running make defconfig")
if run(["make", "defconfig"]).returncode:
    die(f"Error running make defconfig")
