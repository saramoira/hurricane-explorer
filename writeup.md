# Hurricane Mesoscale Browser
Saramoira Shields

## Design 

* Data collection and preprocessing:
I used a combination of the [HURDAT2 Database](https://www.nhc.noaa.gov/data/hurdat/hurdat2-format-atl-1851-2021.pdf) and NOAA's [ADT reports](https://www.ssd.noaa.gov/PS/TROP/2021/adt/archive.html) for Atlantic storms in 2021 to build a csv of storm positions and observations times. I then used the [AWS boto3] library to match observations times to s3 urls of GOES-16 Mesoscale imagery in NetCDF format. For purposes of demonstration I limited this storm list to storms that reached Hurricane strength.
* Image processing and informational plotting: 
I used color processing recipes from the [goes2go](https://blaylockbk.github.io/goes2go/_build/html/) and [satpy](https://satpy.readthedocs.io/en/stable/) packages, as well as an infrared enhancement recipe from [] to produce 8 color plots from the raw infrared channel data in the netCDF files. I also created a geographic plot showing the locations of the mesoscale windows in relation to each storm for each timestamp. Finally, I plotted the infrared reflectance as a 3D surface for better visualization of the relationship between storm reflectance and cloud height.
* App creation:
I built an app using Plotly Dash and Flask that dynamically runs the color processing functions, map plot and 3D surface plot based on a user's selection of storm, relative time, and color processing choice. After testing with locally downloaded netCDF files, I then changed the code to use the s3 bucket locations for scalability. 

## Data

* NOAA's [HURDAT2 Database](https://www.nhc.noaa.gov/data/hurdat/hurdat2-format-atl-1851-2021.pdf) for 2021. 
* NOAA's [ADT Reports](https://www.ssd.noaa.gov/PS/TROP/2021/adt/archive.html).
* The [NOAA GOES-R](https://registry.opendata.aws/noaa-goes/) open dataset on AWS

## Outcome

The app is functional, but the use of the s3 links instead of local files introduced a 2-3 second lag in reading and loading the netCDF files. I plan to utilize AWS Elastic Beanstalk to deploy the app to a server instance running on the same region as the NOAA s3 bucket (us-east-1) in order to speed up the processing in the cloud. One thing that came up while I was working on this project is that netCDF with xarray is not cloud-performant, meaning xarray can't use some of it's more powerful reading features with s3 cloud objects. Because of this, I would also like to use [pangeo-forge] and possibly [kerchunk] to make a consolidated metadata store for each storm, which would hopefully allow for both faster loading and the ability to load each storm as a complete dataset.

## Algorithms/Tools
This project used pandas and boto3 for initial selection and preprocessing, xarray, cartopy, plotly, [satpy](https://satpy.readthedocs.io/en/stable/), and [goes2go](https://blaylockbk.github.io/goes2go/_build/html/) for image processing and plotting, and both Dash and Dash bootstrap components for app creation and layout. 