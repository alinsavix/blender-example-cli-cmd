#!/usr/bin/env python3
# An example of how to make a command line script for being able to make
# commands that do things with blender, but running like you would a normal
# command. In this particular example, we're going to load an obj, add a
# subsurf modifier, and export the updated model as an obj.
#
# Run as e.g. `blender-example-cli-cmd rose.obj rose-subsurf.obj`
#
# If you're running under linux or macOS, you can just set this script
# executable, and call it like any other program, and it will automatically
# detect that it isn't yet running under blender, and then run blender with
# a `--python` argument to itself. On windows, it's easiest to just give
# yourself a batch file to call blender with the appropriate args (an example
# is included)
#
# A normal call to blender to use this script, when not having it automatically
# re-exec itself under blender, would look something like:
#   blender --background --factory-startup --python thisfile.py -- arg1 arg2
#
# Note that blender tends to be *extremely spammy* when it runs, and this
# script doesn't try to hide that. You could potentially adjust the script
# to do something different with stdout/stderr if you wanted, though
#
# The blender executable needs to be in your path.
import argparse
import logging as lg
import os
import platform
import sys
from pathlib import Path
from typing import List


# We need execBlender defined before our `import bpy` try/catch block, to let
# us automatically re-exec ourselves under blender if we're not already
def execBlender(reason: str):
    print("Not running under blender (%s)" % (reason))
    print("Re-execing myself under blender (blender must exist in path)...")

    blender_bin = "blender"
    mypath = str(Path(__file__).resolve())  # get my full path

    # windows fucks up exec() if there are files with spaces in the name, even
    # if you use the exec() version where you pass the args as an array that
    # shouldn't get split on spaces. Stupid hack to fix:
    if platform.system() == "Windows":
        mypath = f'"{mypath}"'

    blender_args = [
        blender_bin,
        "--background",
        "--factory-startup",
        "--python",
        mypath,
        "--",
    ] + sys.argv[1:]

    #  print("executing: %s" % " ".join(blender_args))

    try:
        # exec() and friends never return if successful, so no need to exit
        # or return or anything after this line
        os.execvp(blender_bin, blender_args)
    except OSError as e:
        print(f"ERROR: Couldn't exec blender: {e}")
        sys.exit(1)


# Check if we're running under Blender ... and if not, fix that.
# We both have to check to make sure we can import bpy, *and* check
# to make sure there's something meaningful inside that module (like
# an actual context) because there exist 'stub' bpy modules for
# developing outside of blender, that will still import just fine...)
try:
    import bpy
except ImportError:
    execBlender("no bpy available")


# It imported ok, so now check to see if we have a context object
if bpy.context is None:
    execBlender("no context available")


# small script, cheat and make the logging bits global
LOGGER = lg.getLogger()
LOGLEV = [lg.INFO, lg.DEBUG]
LOGLEV = [None] + sorted(LOGLEV, reverse=True)


# A helper function to clear out the existing scene so we're in a known state
def sceneprep() -> None:
    # Make sure we're in a known/consistent mode (i.e. object mode)
    if bpy.context.active_object is not None:
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj)


def load_obj(file: str) -> None:
    LOGGER.debug(f"Loading obj file '{file}'")
    bpy.ops.import_scene.obj(filepath=file)
    LOGGER.debug(f"successfully loaded obj file '{file}'")


def save_obj(file: str) -> None:
    LOGGER.debug(f"saving obj file '{file}'")
    bpy.ops.export_scene.obj(
        filepath=file,
        check_existing=False,  # overwrite existing
        use_selection=False,  # export all; change to export just selection
        use_animation=False,
        use_mesh_modifiers=True,  # apply modifiers before saving
    )
    LOGGER.debug(f"successfully saved obj file '{file}'")


# the actual work
def thething(args: argparse.Namespace, input: str, output: str) -> int:
    LOGGER.debug(f"doing the thing with input '{input}' and output '{output}'")

    if not os.path.isfile(input):
        LOGGER.error(f"input file '{input}' does not exist or isn't a file")
        return 1

    sceneprep()
    load_obj(input)

    # deselect everything
    bpy.ops.object.select_all(action='DESELECT')

    # cycle through the scene and subdivide every object
    for obj in bpy.data.objects:
        modifier = obj.modifiers.new(name="subsurf", type="SUBSURF")
        modifier.levels = args.levels

    save_obj(output)


# simple argument handling, via argparse
def parse_arguments(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="blender-example-cli-cmd",
        description="An example script that will do some simple thing with blender, from the CLI",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity level (-v for INFO, -vv for DEBUG)"
    )

    parser.add_argument(
        "--levels",
        action="store",
        type=int,
        default=2,
        help="Number of subdivision levels to add",
    )

    parser.add_argument(
        "input",
        type=str,
        help="input file to process",
    )

    parser.add_argument(
        "output",
        type=str,
        help="output file to process",
    )

    parsed_args = parser.parse_args(argv)
    return parsed_args


def main(argv: List[str]) -> int:
    # We get the entirety of blender's command line as argv, we need to trim
    # that down to just our arguments (everything after the `--`)
    args_start = argv.index("--") + 1
    argv = argv[args_start:]

    args = parse_arguments(argv)

    # config the logger to whatever our log level is
    lg.basicConfig(
        level=LOGLEV[min(args.verbose, len(LOGLEV) - 1)],
        format="%(levelname)s: %(message)s",
    )

    LOGGER.debug("got stuff parsed, gonna do the thing!")
    thething(args, args.input, args.output)
    LOGGER.info(f"DONE! {args.input} -> {args.output}")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
