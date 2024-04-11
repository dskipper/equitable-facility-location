# equitable-facility-location

This package selects from a provided collection of possible 
"destinations" to optimize the equitable access of a population 
(located at "origins") to a selected destination.

Equitable access is quantified by the Kolm-Pollak EDE of the 
distribution of distances that individuals must travel to reach 
their assigned destination.

For detailed information about the methodology:
- [Drew Horton, Tom Logan, Joshua Murrell, Daphne Skipper, and Emily Speakman (2024). A Scalable Approach to Equitable Facility Location.](https:||arxiv.org|abs|2401.15452)

## Kolm-Pollak EDE

The Kolm-Pollak EDE is a metric that was developed to rank distributions of environmental harms, such as pollution or distance from a necessary amenity, taking into account both the level and spread of the distribution by penalizing for "bad" values in the distribution (high distance to an amenity in our case)." 
- An equally distributed equivalent (EDE) answers the question, "if everyone's experience were the same, what level would be equivalent to the current unequal distribution? 
- The goal of an EDE is to provide a more accurate measure of the experience of a population than the population mean.
- When applied to a distribution of "bads" (higher values represent a worse experience), an EDE will always be greater than or equal to the mean.
- An *aversion* parameter provides the user control over how much to penalize inequality
    - In a distribution of "bads" *aversion*, $\leq 0$
    - If *aversion* = 0, then the EDE equals the mean
    - As *aversion* becomes more negative, the EDE moves towards the maximum value in the distribution
    - Typically, *aversion* ranges between -1.5 and -0.5

For more information about the Kolm-Pollak EDE:
- [T.M. Logan, M.J. Anderson, T.G. Williams, L. Conrow (2021). Measuring inequalities in urban systems: An approach for evaluating the distribution of amenities and burdens.](
https:||doi.org|10.1016|j.compenvurbsys.2020.101590)

- [G. Sheriff, K.B. Maguire (2020). Health Risk, Inequality Indexes, and Environmental Justice. Risk Analysis: An Official Publication of the Society for Risk Analysis.](https:||research.uintel.co.nz|equality-measure|#:~:text=Sheriff%2C%20G.%2C%20%26%20Maguire%2C%20K.%20B.%20(2020).%20Health%20Risk%2C%20Inequality%20Indexes%2C%20and%20Environmental%20Justice.%20Risk%20Analysis%3A%20An%20Official%20Publication%20of%20the%20Society%20for%20Risk%20Analysis.)

## Getting started

1. Clone the main branch of this repository
2. [Install anaconda](ttps://conda.io/projects/conda/en/latest/user-guide/install/index.html) if you don't already have it
3. In a terminal (an Anaconda terminal on a Windows machine) move into the top level of equitable-facility-location directory. 
    - Run the following command to create a conda environment with the required installations. 
        - `conda env create -f environment.yml`
    - Every time you wish to run the code, activate the newly created conda environment (from any directory): 
        - `conda activate efl`
4. After activating the efl environment, run the following command to enable the command line interface at the top level of the equitable-facility-location directory:
    - `pip install .`
5. Optimizatin solvers:
    - You should now be able to run the code with the default solver, [SCIP](https://www.scipopt.org/).
    - In order to use the commercial solver, [Gurobi](https://www.gurobi.com), you will need to install a [Gurobi license](https://www.gurobi.com/solutions/licensing/).   
6. To test that the environment is setup correctly, run unit tests by evaluating the command `pytest -W ignore` from the top level directory of the  package. Every test should pass or be skipped (tests involving Gurobi will be skipped).

## Entry points

1. Command line interface ("cli")
    - From a command line, activate the efl environment, `conda activate efl`.
    - Run `efl` from the command line (in any directory) with the required optional arguments as described in the next section, including paths to data files.
    - Examples of data files are in the test_data directory: equitable-facility-location/equitable_facility_location/data/test_data
    - Here is an example of a command line run that can be excuted from inside the `equitable-facility-locatin/data/test_data` directory:
        - `efl origins_basic.csv destinations_basic.csv distances_cartesian.csv results/out_basic_cartesian.csv --minimize='locations' --target_ede=225`
2. Package import ("run")
    - From a command line, activate the efl environment, `conda activate efl`.
    - You should now be able to `import optimize from efl` in a .py or .ipynb file to access the "run" method, `optimize.run()`, described below.
    - Here is an example of using the "run" method in a .py file (assuming the file is executed 
    in the directory containing the data files, `equitable-facility-location/data/test_data`):

```{python}
from efl import optimize
import pandas as pd

if __name__ == "__main__":
    orig_df = pd.read_csv('origins_basic.csv')
    dest_df = pd.read_csv('destinations_basic.csv')
    dist_df = pd.read_csv('distances_taxi.csv')

    results = optimize.run(orig_df, dest_df, dist_df, minimize='ede', num_locations=8)
    print(f'optimal Kolm-Pollak EDE: {results.ede_out()}')
```

## Description of "cli" and "run" arguments

### Required data

The first three required arguments are tables of data. 
Via the "cli", these are paths to csv files.
Via "run", these are Pandas DataFrames. 
Examples of the .csv files are provided in `equitable-facility-location/data/test_data`

1. origins table
    - "call method": `argument name` (type)
        - "cli": `origin_file` (path to csv)
        - "run": `origin_df` (Pandas DataFrame)
    - required column : requirements
        - `id` : unique, no missing values
        - `population` : numeric, no missing values
2. destinations table
    - "call method": `argument name` (type)
        - "cli": `destination_file` (path to csv)
        - "run": `destination_df` (Pandas DataFrame)
    - required column : requirements
        - `id` : unique, no missing values
    - optional column : requirements
        - `open` : 'yes' (must select) or 'percent' (select minimum % of these)
        - `capacity` : numeric (use for *individual* destination capacities)
3. distances table
    - "call method": `argument name` (type)
        - "cli": `distance_file` (path to csv)
        - "run": `distance_df` (Pandas DataFrame)
    - must contain one row for each origin, destination pair (may contain extra rows)
    - required column : requirements
        - `origin` : no missing values (id from origin table)
        - `destination` : no missing values (id from destination table)
        - `distance` : numeric, no missing values3. `distance_file`, `distance_df`
4. path to file for solver output 
    - argument name: `out_file` 
    - *required* for "cli"
    - *optional* keyword argument for "run"

### Optional keyword arguments


| `parameter`  | description | requirement or valid values | default |  
| ----------------  | ----------- | --------------------------- | --------- |
| `minimize` | optimization objective | 'ede' or 'locations' | 'ede' |
| `num_locations` | number of destinations to select | *required* if minimize = 'ede' | None |
| `target_ede` | upper bound on Kolm-Pollak EDE | *required* if minimize = 'locations' | None |
| `aversion` | inequality aversion parameter | $x \leq 0$ | $x=-1$ |
| `scaling_factor` | "$\alpha$" in methods paper | numeric | calculated using input data |
| `min_percent` | minimum % of destinations labeled 'percent' to include | $0 \leq x \leq 1$ | $0$ |
| `radius` | exclude (origin, destination) pairs more than radius apart | $x>0$ | None |
| `capacity` | assigned to destinations with no individual capacity | $x>0$ | None |
| `solver` | name of optimization solver | 'scip' or 'gurobi' | 'scip' |
| `time_limit` | limits amount of time in solver (solver returns best solution found so far) | seconds | Solver default |
| `mip_gap` | optimality gap limit (solver returns best solution so far when this gap is reached) | $0 < x < 1$ | Solver default |

## Results

### `model.Results` object

> "run" returns an object of this type

- `model.Results` attributes:
    - `assignment_df` 
        - Pandas DataFrame 
        - one row per origin 
        - columns: 
            - `origin` 
            - `destination` 
            - `population` 
            - `distance`
    - `parameters_dict`
        - dictionary of input parameters 
        - {input_parameter_name : value}
    - `solver_wall_time`
        - length of time (in seconds) the model was with the solver
    - `solver_mip_gap`
        - from solver: (upper bound - lower bound) / (upper bound)

- `model.Results` methods
    - `ede_out()` 
        - Kolm-Pollak EDE of the optimal distribution of distances
    - `mean_distance_out()`
        - mean distance of an individual to assigned destination (in optimal solution)
    - `scaling_factor_out()`
        - scaling parameter associated with optimal solution
    - `num_locations_out()`
        - number of destinations selected by optimal solution
    - `aversion_out()`
        - inequality aversion associated with optimal solution when approximate scaling_factor is accounted for |



### Output files 

> "cli" returns solution via output files. "run" generates output files only if `out_file` is provided.

1. `out_file.csv` (.csv is appended to out_file parameter if necessary)
    - model.Results.assignment_df() saved as a csv

2. `out_file_summary.csv`
    - Columns:
        - `name`
        - `value`
    - Includes all other information from model.Results object including:
        - input parameters
        - other model.Results attributes:
            - 'solver_wall_time'
            - 'solver_mip_gap'
        - values from model.Results methods
            - 'ede_out'
            - 'mean_distance_out'
            - 'num_locations_out'
            - 'scaling_factor_out'
            - 'aversion_out'

## References

- The optimization model is coded using the Python optimization modeling language, Pyomo:

    - Bynum, Michael L., Gabriel A. Hackebeil, William E. Hart, Carl D. Laird, Bethany L. Nicholson, John D. Siirola, Jean-Paul Watson, and David L. Woodruff. Pyomo - Optimization Modeling in Python. Third Edition Vol. 67. Springer, 2021.

    - Hart, William E., Jean-Paul Watson, and David L. Woodruff. "Pyomo: modeling and solving mathematical programs in Python." Mathematical Programming Computation 3(3) (2011): 219-260.

- The SCIP optimization solver, which is generously provided under the [Apache 2.0 License](http://www.apache.org/licenses/LICENSE-2.0), is the default solver:

    - [The SCIP Optimization Suite 9.0](https://optimization-online.org/2024/02/the-scip-optimization-suite-9-0/) *Suresh Bolusani, Mathieu Besançon, Ksenia Bestuzheva, Antonia Chmiela, João Dionísio, Tim Donkiewicz, Jasper van Doornmalen, Leon Eifler, Mohammed Ghannam, Ambros Gleixner, Christoph Graczyk, Katrin Halbig, Ivo Hedtke, Alexander Hoen, Christopher Hojny, Rolf van der Hulst, Dominik Kamp, Thorsten Koch, Kevin Kofler, Jurgen Lentz, Julian Manns, Gioni Mexi, Erik Mühmer, Marc E. Pfetsch, Franziska Schlösser, Felipe Serrano, Yuji Shinano, Mark Turner, Stefan Vigerske, Dieter Weninger, Lixing Xu* Available at [Optimization Online](https://optimization-online.org/2024/02/the-scip-optimization-suite-9-0/) and as [ZIB-Report 24-02-29](https://nbn-resolving.org/urn:nbn:de:0297-zib-95528), February 2024

- The code includes an option to use the commercial solver, Gurobi. As noted above, this option requires a [Gurobi license](https://www.gurobi.com/solutions/licensing/).
    - [Gurobi Optimization, LLC](https://www.gurobi.com). Gurobi Optimizer Reference Manual, 2023.


## How to cite

If you use the equitable-facility-location code base in your work, please cite the following two items:

1. The code in this github repository using the "Cite this repository" dropdown menu

2. The article describing the methodology:
    - Text:

        D. Horton, T. Logan, J. Murrell, D. Skipper, E. Speakman (2024). A Scalable Approach to Equitable Facility Location.  https:\\doi.org\10.48550\arXiv.2401.15452

    - Bibtex: 

        @misc{horton2024scalable,
            title={A Scalable Approach to Equitable Facility Location}, 
            author={Drew Horton and Tom Logan and Joshua Murrell and Daphne Skipper and Emily Speakman},
            year={2024},
            eprint={2401.15452},
            archivePrefix={arXiv},
            primaryClass={math.OC}
        }