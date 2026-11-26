SEBASTIANA INES JOSEFA DE SAN AGUSTIN - EXCLUSIVE CUSTOM SKIN FOR MARTA (Hellish Quart)

A custom skin for Marta only, built on her native 68-joint skeleton.
It uses Marta's original moves and rapier.
Sebastiana Ines Josefa de San Agustin, noblewoman of 18th-century New Spain:
blue brocade gown with lace ruffles and a draped overskirt over a red
floral underskirt.

THE SKIRT IS SIMULATED AS CLOTH
The floor-length skirt is simulated as real cloth and pushed by the legs, so
in normal stances, footwork, lunges and dodges the legs stay inside it.
Known issue: Marta's animations were made for her knee-length dress. When a
knee rises almost to waist height, the thigh can still show above the skirt for
a moment, and small gaps can appear where the overskirt and underskirt cross.

INSTALL
1. Close Hellish Quart.
2. In Steam, right-click Hellish Quart > Manage > Browse local files.
3. Copy these four files into  Hellish Quart_Data\StreamingAssets\ :
     skin_marta_sebastiana
     skin_marta_sebastiana.manifest
     pic_marta_sebastiana
     pic_marta_sebastiana.manifest
4. Start the game, select Marta and choose Sebastiana under Custom Skin.

UNINSTALL
Delete those four files from StreamingAssets.

FIRST PERSON (FPP) - OPTIONAL
The skin works without this. In the game version of November 2026, Marta's
loader ignores custom skins in first person. To see the skin in FPP too,
change 4 bytes of Hellish Quart_Data\resources.assets with a hex editor in
overwrite mode.
Back up the file first. Only do it if the file is exactly 895,141,008 bytes
and the original values match this table:

  Offset (hex)   Original   New
  0x32B93AC0     03         02
  0x32B93AC4     79         6E
  0x32B93AC5     65         6F
  0x32B93AC6     73         00

Save and check that the file size is unchanged. To undo it, restore the backup
or verify the game files in Steam. A game update replaces the file and undoes
the change. The same change serves every Marta skin.

Compatible with other Marta skins installed at the same time (different files).
