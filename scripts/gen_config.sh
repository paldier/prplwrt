#!/bin/sh

[ -f .config ] && {
	echo ".config already exists"
	exit 1
}

for a in $@; do
	[ -f feeds/profiles/$a.profile ] || {
		echo "feeds/profiles/$a.profile does not exist"
		exit 1
	}
done

touch .config

for a in $@; do
	cat feeds/profiles/$a.profile >> .config
done

make defconfig

