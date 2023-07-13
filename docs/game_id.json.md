# [game_id].json specification
#### Version 2.0

Games are saved to disk in the form of [game_id].json files. These files contain all information about a game excluding its cover, which is handled separately.

## Location

The standard location for these files is `/cartridges/games/` under the data directory of the user (`XDG_DATA_HOME` on Linux).

## Contents

The following attributes are saved:

- [added](#added)
- [executable](#executable)
- [game_id](#game_id)
- [source](#source)
- [hidden](#hidden)
- [last_played](#last_played)
- [name](#name)
- [developer](#developer)
- [removed](#removed)
- [blacklisted](#blacklisted)
- [version](#version)

### added

The date at which the game was added.

Cartridges will set the value for itself. Don't touch it.

Stored as a Unix time stamp.

### executable

The executable to run when launching a game.

If the source has a URL handler, using that is preferred. In that case, the value should be `"xdg-open url://example/url"` for Linux and `"start url://example/url"` for Windows.

Stored as either a string (preferred) or an argument vector to be passed to the shell through [subprocess.Popen](https://docs.python.org/3/library/subprocess.html#popen-constructor).

### game_id

The unique ID of the game, prefixed with [`[source]_`](#source) to avoid clashes.

If the game's source uses a consistent internal ID system, use the ID from there. If not, use a hash function that always returns the same hash for the same game, even if some of its attributes change inside of the source.

Stored as a string.

### source

A unique ID for the source of the game in lowercase, without spaces or underscores.

If a source provides multiple internal sources, these should be separately labeled, but share a common prefix. eg. `heoic_gog`, `heroic_epic`. This is the only place you should use an underscore.

Stored as a string.

### hidden

Whether or not a game is hidden.

If the source provides a way of hiding games, take the value from there. Otherwise it should be set to false by default.

Stored as a boolean.

### last_played

The date at which the game was last launched from Cartridges.

Cartridges will set the value for itself. Don't touch it.

Stored as a Unix time stamp. 0 if the game hasn't been played yet.

### name

The title of the game.

Stored as a string.

### developer

The developer or publisher of the game.

If there are multiple developers or publishers, they should be joined with a comma and a space (`, `) into one string.

This is an optional attribute. If it can't be retrieved from the source, don't touch it.

Stored as a string.

### removed

Whether or not a game has been removed.

Cartridges will set the value for itself. Don't touch it.

Stored as a boolean.

### blacklisted

Whether or not a game is blacklisted. Blacklisting a game means it is going to still be imported, but not displayed to the user.

You should only blacklist a game based on information you pull from the web. This is to ensure that games which you would skip based on information online are still skipped even if the user loses their internet connection. If an entry is broken locally, just skip it.

The only reason to blacklist a game is if you find out that the locally cached entry is not actually a game (eg. Proton) or is otherwise invalid.

Unless the above criteria is met, don't touch the attribute.

Stored as a boolean.

### version

The version number of the [game_id].json specification.

Cartridges will set the value for itself. Don't touch it.

Stored as a number.