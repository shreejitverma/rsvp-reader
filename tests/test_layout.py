from rsvpreader.layout import PAD_X, PAD_Y, TICK_GAP, TICK_LENGTH, flow_positions, pivot_box


def test_pivot_box_is_centered_and_fixed():
    box = pivot_box(center_x=500, center_y=300, text_height=40, inner_width=20)
    assert (box.left, box.right) == (500 - 10 - PAD_X, 500 + 10 + PAD_X)
    assert (box.top, box.bottom) == (300 - 20 - PAD_Y, 300 + 20 + PAD_Y)
    assert box.text_top == 300 - 20
    assert box.tick_top == (500, box.top - TICK_GAP, 500, box.top - TICK_GAP - TICK_LENGTH)
    assert box.tick_bottom == (
        500,
        box.bottom + TICK_GAP,
        500,
        box.bottom + TICK_GAP + TICK_LENGTH,
    )


def test_pivot_box_edges_are_whole_pixels_for_odd_sizes():
    box = pivot_box(center_x=514, center_y=300, text_height=61, inner_width=29)
    for edge in (box.left, box.right, box.top, box.bottom, box.text_top):
        assert edge == int(edge), edge
    assert (box.left + box.right) / 2 == 514
    assert (box.top + box.bottom) / 2 == 300
    assert box.right - box.left == 30 + 2 * PAD_X
    assert box.bottom - box.top == 62 + 2 * PAD_Y


def test_flow_positions_right_anchored_ends_at_edge():
    measure = len
    pos = flow_positions(["ab", "cde"], measure, space_width=1, edge_x=100, anchor_right=True)
    assert pos == [(94, "ab"), (97, "cde")]
    last_x, last_word = pos[-1]
    assert last_x + measure(last_word) == 100


def test_flow_positions_left_anchored_starts_at_edge():
    pos = flow_positions(["ab", "cde"], len, space_width=2, edge_x=10, anchor_right=False)
    assert pos == [(10, "ab"), (14, "cde")]


def test_flow_positions_empty():
    assert flow_positions([], len, 1, 0, True) == []
