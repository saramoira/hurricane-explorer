
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import xarray as xr


def get_imshow_kwargs(ds):

    return dict(
        extent=[ds.x2.data.min(), ds.x2.data.max(), ds.y2.data.min(), ds.y2.data.max()],
        transform=ds.crs,
        origin="upper",
        interpolation="none",
    )


def rgb_as_dataset(G, RGB, description, latlon=False):

    # Assemble a new xarray.Dataset for the RGB data
    ds = xr.Dataset({description.replace(" ", ""): (["y", "x", "rgb"], RGB)})
    ds.attrs["description"] = description

    # Convert x, y points to latitude/longitude
    _, crs = field_of_view(G)
    sat_h = G.goes_imager_projection.perspective_point_height
    x2 = G.x * sat_h
    y2 = G.y * sat_h
    ds.coords["x2"] = x2
    ds.coords["y2"] = y2

    ds["x2"].attrs["long_name"] = "x sweep in crs units (m); x * sat_height"
    ds["y2"].attrs["long_name"] = "y sweep in crs units (m); y * sat_height"

    ds.attrs["crs"] = crs

    if latlon:
        X, Y = np.meshgrid(x2, y2)
        a = ccrs.PlateCarree().transform_points(crs, X, Y)
        lons, lats, _ = a[:, :, 0], a[:, :, 1], a[:, :, 2]
        ds.coords["longitude"] = (("y", "x"), lons)
        ds.coords["latitude"] = (("y", "x"), lats)

    # Copy some coordinates and attributes of interest from the original data
    for i in ["x", "y", "t", "geospatial_lat_lon_extent"]:
        ds.coords[i] = G[i]
    for i in [
        "orbital_slot",
        "platform_ID",
        "scene_id",
        "spatial_resolution",
        "instrument_type",
        "title",
    ]:
        ds.attrs[i] = G.attrs[i]

    ## Provide some helpers to plot with imshow
    ds.attrs["imshow_kwargs"] = get_imshow_kwargs(ds)

    return ds


def load_RGB_channels(C, channels):

    # Units of each channel requested
    units = [C["CMI_C%02d" % c].units for c in channels]
    RGB = []
    for u, c in zip(units, channels):
        if u == "K":
            # Convert form Kelvin to Celsius
            RGB.append(C["CMI_C%02d" % c].data - 273.15)
        else:
            RGB.append(C["CMI_C%02d" % c].data)
    return RGB


def gamma_correction(a, gamma):

    # Gamma decoding formula
    return np.power(a, 1 / gamma)


def normalize(value, lower_limit, upper_limit, clip=True):

    norm = (value - lower_limit) / (upper_limit - lower_limit)
    if clip:
        norm = np.clip(norm, 0, 1)
    return norm


# ======================================================================
# ======================================================================


def TrueColor(C, gamma=2.2, pseudoGreen=True, night_IR=True, **kwargs):

    # Load the three channels into appropriate R, G, and B variables
    R, G, B = load_RGB_channels(C, (2, 3, 1))

    R = np.clip(R, 0, 1)
    G = np.clip(G, 0, 1)
    B = np.clip(B, 0, 1)

    R = gamma_correction(R, gamma)
    G = gamma_correction(G, gamma)
    B = gamma_correction(B, gamma)

    if pseudoGreen:
        # Calculate the "True" Green
        G = 0.45 * R + 0.1 * G + 0.45 * B
        G = np.clip(G, 0, 1)

    if night_IR:
        # Load the Clean IR channel
        IR = C["CMI_C13"]
        # Normalize between a range and clip
        IR = normalize(IR, 90, 313, clip=True)
        # Invert colors so cold clouds are white
        IR = 1 - IR
        # Lessen the brightness of the coldest clouds so they don't
        # appear so bright when we overlay it on the true color image
        IR = IR / 1.4
        # RGB with IR as greyscale
        RGB = np.dstack([np.maximum(R, IR), np.maximum(G, IR), np.maximum(B, IR)])
    else:
        RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "True Color", **kwargs)


def NaturalColor(C, gamma=0.8, pseudoGreen=True, night_IR=False, **kwargs):
   
    def breakpoint_stretch(C, breakpoint):
 
        lower = normalize(C, 0, 10)  # Low end
        upper = normalize(C, 10, 255)  # High end


        combined = np.minimum(lower, upper)

        return combined

    # Load the three channels into appropriate R, G, and B variables
    R, G, B = load_RGB_channels(C, (2, 3, 1))

    # Apply range limits for each channel. RGB values must be between 0 and 1
    R = np.clip(R, 0, 1)
    G = np.clip(G, 0, 1)
    B = np.clip(B, 0, 1)

    if pseudoGreen:
        # Derive pseudo Green channel
        G = 0.45 * R + 0.1 * G + 0.45 * B
        G = np.clip(G, 0, 1)

    # Convert Albedo to Brightness, ranging from 0-255 K
    R = np.sqrt(R * 100) * 25.5
    G = np.sqrt(G * 100) * 25.5
    B = np.sqrt(B * 100) * 25.5

    # Apply contrast stretching based on breakpoints
    R = breakpoint_stretch(R, 33)
    G = breakpoint_stretch(G, 40)
    B = breakpoint_stretch(B, 50)

    if night_IR:
        # Load the Clean IR channel
        IR = C["CMI_C13"]
        # Normalize between a range and clip
        IR = normalize(IR, 90, 313, clip=True)
        # Invert colors so cold clouds are white
        IR = 1 - IR
        # Lessen the brightness of the coldest clouds so they don't
        # appear so bright when we overlay it on the true color image
        IR = IR / 1.4
        # Overlay IR channel, as greyscale image (use IR in R, G, and B)
        RGB = np.dstack([np.maximum(R, IR), np.maximum(G, IR), np.maximum(B, IR)])
    else:
        RGB = np.dstack([R, G, B])

    # Apply a gamma correction to the image
    RGB = gamma_correction(RGB, gamma)

    return rgb_as_dataset(C, RGB, "Natural Color", **kwargs)



def DayCloudPhase(C, **kwargs):
  
    # Load the three channels into appropriate R, G, and B variables
    R, G, B = load_RGB_channels(C, (13, 2, 5))

    # Normalize each channel by the appropriate range of values. (Clipping happens inside function)
    R = normalize(R, -53.5, 7.5)
    G = normalize(G, 0, 0.78)
    B = normalize(B, 0.01, 0.59)

    # Invert R
    R = 1 - R

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Day Cloud Phase", **kwargs)


def DayConvection(C, **kwargs):
    
    # Load the three channels into appropriate R, G, and B variables
    # NOTE: Each R, G, B is a channel difference.
    R = C["CMI_C08"].data - C["CMI_C10"].data
    G = C["CMI_C07"].data - C["CMI_C13"].data
    B = C["CMI_C05"].data - C["CMI_C02"].data

    # Normalize each channel by the appropriate range of values.
    R = normalize(R, -35, 5)
    G = normalize(G, -5, 60)
    B = normalize(B, -0.75, 0.25)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Day Convection", **kwargs)


def DayCloudConvection(C, **kwargs):

    # Load the three channels into appropriate R, G, and B variables
    R, G, B = load_RGB_channels(C, (2, 2, 13))

    # Normalize each channel by the appropriate range of values.
    R = normalize(R, 0, 1)
    G = normalize(G, 0, 1)
    B = normalize(B, -70.15, 49.85)

    # Invert B
    B = 1 - B

    # Apply the gamma correction to Red channel.
    #   corrected_value = value^(1/gamma)
    gamma = 1.7
    R = gamma_correction(R, gamma)
    G = gamma_correction(G, gamma)

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Day Cloud Convection", **kwargs)



def WaterVapor(C, **kwargs):
   
    # Load the three channels into appropriate R, G, and B variables.
    R, G, B = load_RGB_channels(C, (13, 8, 10))

    # Normalize each channel by the appropriate range of values. e.g. R = (R-minimum)/(maximum-minimum)
    R = normalize(R, -70.86, 5.81)
    G = normalize(G, -58.49, -30.48)
    B = normalize(B, -28.03, -12.12)

    # Invert the colors
    R = 1 - R
    G = 1 - G
    B = 1 - B

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Water Vapor", **kwargs)


def DifferentialWaterVapor(C, **kwargs):

    # Load the three channels into appropriate R, G, and B variables.
    R = C["CMI_C10"].data - C["CMI_C08"].data
    G = C["CMI_C10"].data - 273.15
    B = C["CMI_C08"].data - 273.15

    # Normalize each channel by the appropriate range of values. e.g. R = (R-minimum)/(maximum-minimum)
    R = normalize(R, -3, 30)
    G = normalize(G, -60, 5)
    B = normalize(B, -64.65, -29.25)

    # Gamma correction
    R = gamma_correction(R, 0.2587)
    G = gamma_correction(G, 0.4)
    B = gamma_correction(B, 0.4)

    # Invert the colors
    R = 1 - R
    G = 1 - G
    B = 1 - B

    # The final RGB array :)
    RGB = np.dstack([R, G, B])

    return rgb_as_dataset(C, RGB, "Differential Water Vapor", **kwargs)
