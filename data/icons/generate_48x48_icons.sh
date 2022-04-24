
subdirs="categories"

for subdir in $subdirs; do
	cd scalable/$subdir
	for i in *.svg;do
		target="../48x48/"$( echo $i | cut -d . -f -1 ).png
		echo "converting $i to $target"
		if [ ! -e $target ]; then
			inkscape --without-gui --export-png=$target --export-dpi=72 --export-background-opacity=0 --export-width=48 --export-height=48 "$i";done
		fi
	cd -
done
