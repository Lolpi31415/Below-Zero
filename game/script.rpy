# The script of the game goes in this file.

# Declare characters used by this game. The color argument colorizes the
# name of the character.

define t = Character("Tweedle")

image t normal = Image("characterplaceholder.png", oversample = 2.0)
# The game starts here.
image bg cave = Transform("cavebg.jpg", zoom=3)
label start:

    # Show a background. This uses a placeholder by default, but you can
    # add a file (named either "bg room.png" or "bg room.jpg") to the
    # images directory to show it.

    scene bg cave

    # This shows a character sprite. A placeholder is used, but you can
    # replace it by adding a file named "eileen happy.png" to the images
    # directory.
    show t normal

    # These display lines of dialogue.

    t "You've created a new Ren'Py game."

    t "Once you add a story, pictures, and music, you can release it to the world!"

    # This ends the game.

    return
