import os
import ast
import random
import A_STAR.Repeated_AStar as astar
import map_class
import sys
import multiprocessing as mp
import concurrent.futures as pp
import time

MAZE_PATH = "saved_mazes"
POS_PATH = "saved_pos"
STATS_PATH = "stats"


def load_map(path, fileName):
    # Opens first maze file
    with open(os.path.join(path, fileName), 'r') as file:
        # Gets grid in string form
        grid_str = file.readline()
        # converts string to list of lists
        return ast.literal_eval(grid_str)


def find_obstacles(maze):
    # Iterate through the maze, if we see objects add (x,y) to the list
    obstacles = []
    for row, _ in enumerate(maze):
        for col, cell in enumerate(maze[row]):
            if cell == 1:
                obstacles.append((row, col))
    return obstacles


def generate_pos(maze_size, other_pos=[]):
    row = random.randint(0, maze_size-1)
    col = random.randint(0, maze_size-1)

    # invalid positions include obstacles and goal or agent states already added
    invalid_positions = [val for val in other_pos]

    # keep generating positions until they are valid
    while (row, col) in invalid_positions:
        row = random.randint(0, maze_size-1)
        col = random.randint(0, maze_size-1)

    return (row, col)


def maze_size(mazeName):
    # Get maze size from name
    return int(mazeName.split("_")[1])


def rand_positions(maze, mazeName):
    # get size of map
    size = maze_size(mazeName)
    # Find obstacles so we know where to randomize our spawns
    # Find random pos
    obstacles = find_obstacles(maze)
    start = generate_pos(size, obstacles)
    goal = generate_pos(size, obstacles+[start])
    return start, goal


def save_positions():
    if not os.path.exists(POS_PATH):
        os.makedirs(POS_PATH)
    for mazeName in os.listdir(MAZE_PATH):
        # Load a maze for every file
        maze = load_map(MAZE_PATH, mazeName)
        start, goal = rand_positions(maze, mazeName)
        with open(os.path.join(POS_PATH, mazeName), "w+") as f:
            # Print our stats in sorted order if we didn't encounter valid maps
            f.write(str(start)+"\n")
            f.write(str(goal))


def get_saved_positions(mazeName):
    if not os.path.exists(POS_PATH):
        return "run save_positions() first"
    else:
        with open(os.path.join(POS_PATH, mazeName), "r") as f:
            try:
                start = ast.literal_eval(f.readline())
                goal = ast.literal_eval(f.readline())
                return start, goal
            except Exception:
                return "FILE " + mazeName + " ERROR"


def run_tests(i, bad_maps, stats, count):
    print("Started Process %d" % i)
    t0 = time.time()

    for mazeName in os.listdir(MAZE_PATH):
        # Load a maze for every file, size of maze is in the name
        maze = load_map(MAZE_PATH, mazeName)
        size = maze_size(mazeName)
        # start, goal = rand_positions(maze, mazeName)
        start, goal = get_saved_positions(mazeName)
        # Get a star results on the maze and start/goal, and get the cells that were expanded
        a_star_res, expanded = astar.forward_astar(maze, goal, start)

        # If goal state was found (non empty values returned)
        if a_star_res and expanded:
            # count maze as valid
            count[size] += 1

            # Length of shortest path
            shortest_path = len(a_star_res)

            # Number of expanded cells
            total_expanded = len(a_star_res) + len(expanded)

            # Add the lengths to the appropriate container,
            # we will average this later based on count[size]
            stats[size]['shortest'] += shortest_path
            stats[size]['total'] += total_expanded
        else:
            # If invalid maze add it to bad_map
            bad_maps[size].append(mazeName)

    t1 = time.time() - t0

    print('Process {}, Elapsed Time: {}'.format(
        i, time.strftime("%H:%M:%S", time.gmtime(t1))))


if __name__ == "__main__":
    start_time = time.time()
    maze_sizes = [20, 50, 100]
    test_num = 5
    
    # map_class.generate_maze(count=200, size=20)
    # map_class.generate_maze(count=200, size=50)
    # map_class.generate_maze(count=200, size=100)
    # save_positions()

    # Because we are doing multiprocessing we have to initialize our data structures using Manager()
    mgr = mp.Manager()

    bad_maps = mgr.dict()
    stats = mgr.dict()
    count = mgr.dict()

    # In order for nested structures to update they also have to be initialized via Manager()
    for m in maze_sizes:
        count[m] = 0
        bad_maps[m] = mgr.list()
        stats[m] = mgr.dict()
        stats[m]['shortest'] = 0
        stats[m]['total'] = 0

    runs = 4  # number of runs we are doing of the whole directory
    jobs = []
    for i in range(runs):  # loop through directory n times
        p = mp.Process(target=run_tests, args=(
            i, bad_maps, stats, count,))
        jobs.append(p)
        p.start()

    for j in jobs:
        j.join()

    # Create stats dir if it doesnt exist
    if not os.path.exists(STATS_PATH):
        os.makedirs(STATS_PATH)

    # Average the path lengths and log them, test_num is the manually adjusted run we are doing
    # Runs = 4
    # 0 = Repeated A* forward  g = euclidean dist (start, curr)
    # 1 = Repeated A* backward  g = euclidean dist (start, curr)
    # 2 = Repeated A* forward  g=1
    # 3 = Repeated A* backward  g=1
    # 4 = Repeated A* forward  g = parent_cost + 1 rand
    # 5 = Repeated A* backward  g = parent_cost + 1 rand
    
    with open(os.path.join(STATS_PATH, 'stats-euclid ' + str(test_num) + ".txt"), "w+") as f:
        # Print our stats in sorted order if we didn't encounter valid maps
        f.write("Runs: %d \n" % runs)
        for size, s in sorted(stats.items()):
            if count[size] == 0:
                continue
            f.write("Stats for: %d \n" % size)
            f.write("AVG. PATH LEN: {}\n".format(s['shortest']//count[size]))
            f.write("AVG. EXPANDED: {}\n".format(s['total'] // count[size]))

        # Convert listproxies to normal lists
        for k, v in bad_maps.items():
            if v:
                bad_maps[k] = list(v)
            else:
                del bad_maps[k]

        count_badmaps = sum(len(values) for values in bad_maps.values())
        count_total = sum(values for values in dict(count).values())

        end_time = time.time() - start_time

        # f.write("TOTAL MAPS: {}\nBAD MAPS:{} {}\n RUN TIME: {}".format(
        #     count_total, count_badmaps, dict(bad_maps), time.strftime("%H:%M:%S", time.gmtime(end_time))))

        print('Elapsed Time Total: {}'.format(
            time.strftime("%H:%M:%S", time.gmtime(end_time))))
