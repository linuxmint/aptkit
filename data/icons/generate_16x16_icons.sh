# we need to generate the 24x24 icons from the 22x22 tango icons
subdirs="categories status"

for subdir in $subdirs; do
	cd 22x22/$subdir
	for icon in *.png; do
		target="../../16x16/$subdir/$icon"
		if [ ! -e $target ]; then
			convert -resize 16x16 $icon $target;
		fi
	done
	cd -
done

