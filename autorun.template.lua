fm.autorun = {
    name = "%%NAME%%", --you can specify the image folder name like this if you don't want to use the save name.
    day = true,
    night = true,
    around_build_range = 5.2,
    smaller_types = {"lamp", "electric-pole", "radar", "straight-rail", "curved-rail", "rail-signal", "rail-chain-signal", "locomotive", "cargo-wagon", "fluid-wagon", "car"},
    around_smaller_range = 1,
    date = "%%DATE%%",
    mapInfo = %%MAPINFO%%,
    chunkCache = %%CHUNKCACHE%%
}