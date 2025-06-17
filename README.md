# CamoSwatchesPy
Merging and analyzing Sentiel 2A Satellite data in order to scientifically analyze which camoflauge will be most effective in a given area at a given time of year.

Would like to incorporate sub-pixel analysis, additional bands, and a flora API in the near future to further improve color predictions.

Serves as the backend of my camoflauge-pattern/color matching site. FastAPI enables the front end to make easy API calls to this software, which then returns results. Given the large size of the sattelite rasters, I used buffers to efficiently pass around data so we aren't saving anything to disk uncessarily.

Due to worst case scenario O(N^2) complexity of comparing each color to one another using the CIED2000 formula I wrote a dll in c++ to speed up the process. While there are other algorithims & methods of stratifying/combining colors with better run times, they are not sufficiently accurate enough for my liking. 

# Flow

Frontend makes API call through fast api ->
