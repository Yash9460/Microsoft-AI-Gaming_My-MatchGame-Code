#_  __  __       _       _        ____
#  |  \/  | __ _| |_ ___| |__    / ___| __ _ _ __ ___   ___
#  | |\/| |/ _` | __/ __| '_ \  | |  _ / _` | '_ ` _ \ / _ \
#  | |  | | (_| | || (__| | | | | |_| | (_| | | | | | |  __/
#  |_|  |_|\__,_|\__\___|_| |_|  \____|\__,_|_| |_| |_|\___|
#
botName='byash2060-defbot'
import requests
import json
from random import sample, choice
from time import sleep

# See our help page to learn how to get a WEST EUROPE Microsoft API Key at
#  https://help.aigaming.com/game-help/signing-up-for-azure
#                                              *** Use westeurope API key for best performance ***
headers_vision = {'Ocp-Apim-Subscription-Key': 'YOUR-WESTEUROPE-MICROSOFT-COMPUTER-VISION-API-KEY', 'Content-Type': 'application/octet-stream'}
vision_base_url = "https://westeurope.api.cognitive.microsoft.com/vision/v2.0/"

analysed_tiles = []
previous_move = []
api_calls = []
move_number = 0

# =============================================================================
# calculate_move() overview
#  1. Analyse the upturned tiles and remember them
#  2. Determine if you have any matching tiles
#  3. If we have matching tiles:
#        use them as a move
#  4. If no matching tiles:
#        Guess two tiles for this move
#
#  **Important**: calculate_move() can only remember data between moves
#    if we store data in a global variable
#  Use the analysed_tiles global to remember the tiles we have seen
#  We recognise animals for you, you must add Landmarks and Words
#
#  Get more help on the Match Game page at https://help.aigaming.com
#
def calculate_move(gamestate):
    global analysed_tiles
    global previous_move
    global move_number

    # Record the number of tiles so we know how many tiles we need to loop through
    num_tiles = len(gamestate["Board"])

    move_number += 1
    if gamestate["UpturnedTiles"] == []:
      print("{}. No upturned tiles for this move.".format(move_number))
    else:
      print("{}. ({}, {}) Upturned tiles for this move".format(move_number, gamestate["UpturnedTiles"][0]["Index"], gamestate["UpturnedTiles"][1]["Index"]))
    print("  gamestate: {}".format(gamestate))

    # If we have not yet used analysed_tiles (i.e. It is the first turn of the game)
    if analysed_tiles == []:
        # Create a list to hold tile information and set each one as UNANALYSED
        for index in range(num_tiles):
            # Mark tile as not analysed
            analysed_tiles.append({})
            analysed_tiles[index]["State"] = "UNANALYSED"
            analysed_tiles[index]["Subject"] = None

    # The very first move in the game does not have any upturned tiles, and
    # if your last move matched tiles, you will not have any upturned tiles

    # Check to see if we have received some upturned tiles for this move.
    if gamestate["UpturnedTiles"] != []:
        # Analyse the tile images using the Microsoft API and store the results
        # in analysed_tiles so that we don't have to analyse them againf if we
        # see the same tile later in the game.
        analyse_tiles(gamestate["UpturnedTiles"], gamestate)
    # Else, it is either our first turn, or, our previous move was a match
    else:
        # If it is not our first move of the game
        if previous_move != []:
            # then our previous move successfully matched two tiles
            # Update our analysed_tiles to mark the previous tiles as matched
            print("  MATCH: ({}, {}) - {}".format(previous_move[0], previous_move[1], analysed_tiles[previous_move[0]]["Subject"]))
            analysed_tiles[previous_move[0]]["State"] = "MATCHED"
            analysed_tiles[previous_move[1]]["State"] = "MATCHED"

    # TIP: Python print statements appear in column 3 of this Editor window
    #      and can be used for debugging
    # Print out the updated analysed_tiles list to see what it contains
    #print("Analysed Tiles: {}".format(json.dumps(analysed_tiles, indent=2)))

    # Check the stored tile information in analysed_tiles
    # to see if we know of any matching tiles
    match = search_for_matching_tiles()
    # If we do have some matching tiles
    if match is not None:
        # Print out the move for debugging ----------------->
        print("  Matching Move: {}".format(match))
        # Set our move to be these matching tiles
        move = match
    # If we don't have any matching tiles
    else:
        # Create a list of all the tiles that we haven't analysed yet
        unanalysed_tiles = get_unanalysed_tiles()
        # If there are some tiles that we haven't analysed yet
        if unanalysed_tiles != []:
            # Choose the unanalysed tiles that you want to turn over
            # in your next move. We turn over a random pair of
            # unanalysed tiles, but, could you make a more intelligent
            # choice?
            move = sample(unanalysed_tiles, 2)
            # Print out the move for debugging  ----------------->
            print("  New tiles move: {}".format(move))
        # If the unanalysed_tiles list is empty (all tiles have been analysed)
        else:
            # If all else fails, we will need to manually match each tile

            # Create a list of all the unmatched tiles
            unmatched_tiles = get_unmatched_tiles()

            # Turn over two random tiles that haven't been matched
            # TODO: It would be more efficient to remember which tiles you
            #       have tried to match.
            move = sample(unmatched_tiles, 2)
            # Print the move for debugging ----------------->
            print("  Random guess move: {}".format(move))

    # Store our move to look back at next turn
    previous_move = move
    # Return the move we wish to make
    return {"Tiles": move}


# Get the unmatched tiles
#
# Outputs:
#   list of integers - A list of unmatched tile numbers
#
# Returns the list of tiles that haven't been matched
def get_unmatched_tiles():
    # Create a list of all the unmatched tiles
    unmatched_tiles = []
    # For every tile in the game
    for index, tile in enumerate(analysed_tiles):
        # If that tile hasn't been matched yet
        if tile["State"] != "MATCHED":
            # Add that tile to the list of unmatched tiles
            unmatched_tiles.append(index)
    # Return the list
    return unmatched_tiles


# Identify all of the tiles that we have not yet analysed with the
# Microsoft API.
#
# Output:
#  list of integers - only those tiles that have not yet been analysed
#                     by the Microsoft API
#
# Returns the list of tiles that haven't been analysed
# (according to analysed_tiles)
def get_unanalysed_tiles():
    # Filter out analysed tiles
    unanalysed_tiles = []
    # For every tile that hasn't been matched
    for index, tile in enumerate(analysed_tiles):
        # If the tile hasn't been analysed
        if tile["State"] == "UNANALYSED":
            # Add that tile to the list of unanalysed tiles
            unanalysed_tiles.append(index)
    # Return the list
    return unanalysed_tiles


# Analyses a list of tiles
#
# Inputs:
#   tiles:       list of JSON objects - A list of tile objects that contain a
#                                       url and an index
#   gamestate:   JSON object          - The current state of the game
#
# Given a list of tiles we want to analyse and the animal list, calls the
# analyse_tile function for each of the tiles in the list
def analyse_tiles(tiles, gamestate):
    # For every tile in the list 'tiles'
    for tile in tiles:
        # Call the analyse_tile function with that tile
        # along with the gamestate
        analyse_tile(tile, gamestate)


# Analyses a single tile
#
# Inputs:
#   tile:      JSON object - A tile object that contains a url and an index
#   gamestate: JSON object - The current state of the game
#
# Given a tile, analyse it to determine its subject and record the information
# in analysed_tiles using the Microsoft APIs
def analyse_tile(tile, gamestate):
    # If we have already analysed the tile
    if analysed_tiles[tile["Index"]]["State"] != "UNANALYSED":
        # We don't need to analyse the tile again, so stop
        return

    # Call analysis
    analyse_url = vision_base_url + "analyze"
    params_analyse = {'visualFeatures': 'categories,tags,description,faces,imageType,color',
                      'details': 'celebrities,landmarks'}
    data = {"url": tile["Tile"]}
    msapi_response = microsoft_api_call(analyse_url, params_analyse, headers_vision, data)
    print("  API Result tile #{}: {}".format(tile["Index"], msapi_response))
    # Check if the subject of the tile is a landmark
    subject = check_for_landmark(msapi_response)
    # If we haven't determined the subject of the image yet
    if subject is None:
        # Check if the subject of the tile is an animal
        subject = check_for_animal(msapi_response, gamestate["AnimalList"])
        # If we still haven't determined the subject of the image yet
        if subject is None:
            # TODO: Use the Microsoft OCR API to determine if the tile contains a
            # word. You can get more information about the Microsoft Cognitive API
            # OCR function at:
            # https://westus.dev.cognitive.microsoft.com/docs/services/56f91f2d778daf23d8ec6739/operations/56f91f2e778daf14a499e1fc
            # Use our previous example to check_for_animal as a guide
            pass
        else:
            print("  Animal at tile #{}: {}".format(tile["Index"], subject))
    # Remember this tile by adding it to our list of known tiles
    # Mark that the tile has now been analysed
    analysed_tiles[tile["Index"]]["State"] = "ANALYSED"
    analysed_tiles[tile["Index"]]["Subject"] = subject


# Check Microsoft API response to see if it contains information about an animal
#
# Inputs:
#   msapi_response: JSON dictionary - A dictionary containing all the
#                                     information the Microsoft API has returned
#   animal_list:    list of strings - A list of all the possible animals in
#                                     the game
# Outputs:
#   string - The name of the animal
#
# Given the result of the Analyse Image API call and the list of animals,
# returns whether there is an animal in the image
def check_for_animal(msapi_response, animal_list):
    # Initialise our subject to None
    subject = None
    # If the Microsoft API has returned a list of tags
    if "tags" in msapi_response:
    # Loop through every tag in the returned tags, in descending confidence order
        for tag in sorted(msapi_response["tags"], key=lambda x: x['confidence'], reverse=True):
            # If the tag has a name and that name is one of the animals in our list
            if "name" in tag and tag["name"] in animal_list:
                # Record the name of the animal that is the subject of the tile
                # (We store the subject in lowercase to make comparisons easier)
                subject = tag["name"].lower()
                # Print out the animal we have found here for debugging ----------------->
                print("  Animal: {}".format(subject))
                print("***API: {}".format(json.dumps(msapi_response,indent=2)))
                # Exit the for loop
                break
    # Return the subject
    return subject


# ----------------------------------- TODO -----------------------------------
#
# Inputs:
#   msapi_response: JSON dictionary - A dictionary containing all the
#                                     information the Microsoft API has returned
# Outputs:
#   string - The name of the landmark
#
# Given the result of the Analyse Image API call, returns whether there is a
# landmark in the image
#
# NOTE: you don't need a landmark_list like you needed an animal_list in check_for_animal
#
def check_for_landmark(msapi_response):
    # TODO: We strongly recommend copying the result of the Microsoft API into
    # a JSON formatter (e.g. https://jsonlint.com/) to better understand what
    # the API is returning and how you will access the landmark information
    # that you need.
    # Here is an example of accessing the information in the JSON:
    # msapi_response["categories"][0]["detail"]["landmarks"][0]["name"].lower()

    # Initialise our subject to None
    subject = None
    for category in msapi_response["categories"]:

        if "detail" in category \
            and "landmarks" in category["detail"] \
            and category["detail"]["landmarks"]:
            # (We store the subject in lowercase to make comparisons easier)
                subject = category["detail"]["landmarks"][0]["name"].lower()
            # Print out the animal we have found here for debugging ----------------->
            #print("  Landmark: {}".format(subject))
            # Exit the for loop
        break
    # Return the subject
    return subject


# Find matching tile subjects
#
# Outputs:
#   list of integers - A list of two tile indexes that have matching subjects
#
# Search through analysed_tiles for two tiles recorded
# under the same subject
def search_for_matching_tiles():
    # For every tile subject and its index
    for index_1, tile_1 in enumerate(analysed_tiles):
        # Loop through every tile subject and index
        for index_2, tile_2 in enumerate(analysed_tiles):
            # If the two tile's subject is the same and isn't None and the tile
            # hasn't been matched before, and the tiles aren't the same tile
            if tile_1["State"] == tile_2["State"] == "ANALYSED" and tile_1["Subject"] == tile_2["Subject"] and tile_1["Subject"] is not None and index_1 != index_2:
                # Choose these two tiles
                # Return the two chosen tiles as a list
                return [index_1, index_2]
    # If we have not matched any tiles, return no matched tiles
    return None


# Call the Microsoft API to analyse the image and to return information
# about the contents of the image.
#
# Inputs:
#   url:     string     - The Microsoft API endpoint
#   params:  dictionary - Which Computer Vision services should the request check for
#   headers: dictionary - API Key to allow request to be made
#   data:    dictionary - The image that we want the API to analyse
# Outputs:
#   JSON dictionary - The result of the API call
#
def microsoft_api_call(url, params, headers, data):
    retry_count=0
    res = {}

    while ("error" in res and res["error"]["code"] == "429") or res == {}:
      # Make API request and record the results
      try:
        r = requests.get(data["url"], allow_redirects=True)
        response = requests.post(url, headers=headers_vision, params=params, data=r.content)
        res = response.json()  # Convert result to JSON
      except Exception as e:
        retry_count += 1
        #print(f"  [WARN] ({retry_count}) There was an issue making the Microsoft API request, retrying...")
        #print(f"    {e}")

    return res


# Test the user has used a valid subscription key
#
# Make a test call to the API to see if it responds correctly. Raise an error if the user's
# API key is not valid for the Microsoft Computer Vision API call
def valid_subscription_key():
    # Make a computer vision api call
    params_analyse = {'visualFeatures': 'categories,tags',
                      'details': 'landmarks'}
    data = {"url": "https://www.aigaming.com/Images/aiWebsiteLogo.png"}

    test_api_call = microsoft_api_call(vision_base_url + "analyze", params_analyse, headers_vision, data)

    if "error" in test_api_call:
        raise ValueError("Invalid Microsoft Computer Vision API key for current region: {}".format(test_api_call))


# Check the subscription key
valid_subscription_key()
