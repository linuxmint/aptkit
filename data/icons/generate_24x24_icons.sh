# we need to generate the 24x24 icons from the 22x22 tango icons
subdirs="categories status"

for subdir in $subdirs; do
	cd 22x22/$subdir
	for icon in *.png; do
		target="../../24x24/$subdir/$icon"
		if [ ! -e $target ]; then
			convert -bordercolor Transparent -border 1x1 $icon $target;
		fi
	done
	cd -
done

