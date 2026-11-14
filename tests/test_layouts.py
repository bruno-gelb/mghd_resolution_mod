from mghd_resolution_mod import layouts
from conftest import make_layout


def originals():
    return {size: make_layout(size) for size in layouts.ORIGINAL_SIZES}


def test_anchored_words_follow_the_new_size():
    generator = layouts.Generator(originals())
    words = layouts.to_words(generator.generate((3440, 1440)))
    assert words[1:3] == (3440, 1440)
    assert words[5] == 3440 - 130  # right
    assert words[6] == 1440 - 40   # bottom
    assert abs(words[7] - (3440 // 2 - 113)) <= 1  # centered
    assert words[3:5] == (12, 30) and words[8:11] == (5, 1000, 77)  # fixed


def test_generated_layouts_are_not_learned_from():
    files = originals()
    files[(3440, 1440)] = b"\0" * 8
    assert (3440, 1440) not in layouts.Generator(files).files


def test_base_is_the_closest_height_at_or_below():
    generator = layouts.Generator(originals())
    assert generator.base_for((3440, 1440))[1] == 1200
    assert generator.base_for((2560, 1080))[1] == 1080


def test_sizes_to_make():
    sizes = layouts.sizes_to_make([(3440, 1440), (1920, 1080), (5000, 2000)], [(1720, 720), (640, 480), (1720, 720)])
    assert (5000, 2000) in sizes and (1720, 720) in sizes
    assert (1920, 1080) not in sizes and (640, 480) not in sizes
    assert sizes.count((3440, 1440)) == 1 and sizes == sorted(sizes)


def test_names():
    assert layouts.file_name((2560, 1080)) == "UIData_2560_1080.dat"
    assert layouts.parse_name("uidata_2560_1080.DAT") == (2560, 1080)
    assert layouts.parse_name("UIData_x.dat") is None
