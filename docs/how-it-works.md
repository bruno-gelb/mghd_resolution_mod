# How it works

[Majesty Gold HD][steam] picks its interface layout from `Data/UIData_<width>_<height>.dat` files: where the map,
the panels, the minimap and the buttons go, for one screen size. It ships 13 of them, up to 1920x1200. On a bigger
screen it uses the closest one, in a black frame in the middle. The mod changes two things, and nothing else: the
game's program, rules, AI and saves stay exactly as they were. The program keeps the original files it changes and
puts them back when you remove the mod.

1. **New layouts.** The program makes layouts for common screen sizes the game lacks (16:9 and 16:10 up to 4K, 21:9
   and 32:9 ultrawides, laptop sizes) and for your own screens, on your computer, from the game's own 13. The game's
   layouts share most of their structure, so comparing them shows which positions follow the right or bottom edge or
   the center of the screen, and those are moved for the new size. The rest were placed by hand for each screen
   height, and come from the game's layout with the closest height. The game lists them by itself: its settings menu
   shows the resolutions with a layout in green.
2. **The version line on the main menu**, under the picture, gets the mod's name and version in front:
   `mghd-resolution-mod 0.1.0. game Version 1.5.2.24`. The text is in the game's text files, `Data/textdata.cam`
   and, for the expansion, `DataMX/mx_textdata.cam`; the box it's drawn in is in each layout, and is made wider, so
   the longer line fits.

The game's interface doesn't scale: a bigger layout shows more of the map, and the text stays the same size in
pixels. On a big screen, a lower resolution of the same shape, scaled up, keeps the text readable.

All the details, with offsets and addresses: [findings](findings.md).

[steam]: https://store.steampowered.com/app/73230/
