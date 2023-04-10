from gi.repository import GdkPixbuf, GLib


def display_animation(
    function, path=None, animation=None, parent_widget=None, game_id=None
):
    if not animation:
        animation = GdkPixbuf.PixbufAnimation.new_from_file(str(path))

    anim_iter = animation.get_iter()

    def update_animation():
        nonlocal anim_iter

        if parent_widget and parent_widget.current_anim != game_id:
            return

        anim_iter.advance()
        pixbuf = anim_iter.get_pixbuf().scale_simple(
            200, 300, GdkPixbuf.InterpType.BILINEAR
        )
        GLib.timeout_add(anim_iter.get_delay_time(), update_animation)
        function(pixbuf)

    update_animation()
