r"""Script to run through a processing task with the processor class.

Run command:

cd .\prototypes\rainfall
streamlit run .\rain_script.py

"""


from hydrobot.htmlmerger import HtmlMerger
from hydrobot.rf_processor import RFProcessor

#######################################################################################
# Reading configuration from config.yaml
#######################################################################################
data, ann = RFProcessor.from_config_yaml("ltco_config.yaml", fetch_quality=True)
data.check_data["Value"] *= 1000
data.quality_data = data.quality_data[data.quality_data["Value"] > 0]

#######################################################################################
# Assign quality codes
#######################################################################################
print("500 ", data.calculate_common_offset(500))
#######################################################################################
# Launch Hydrobot Processing Visualiser (HPV)
# Known issues:
# - No manual changes to check data points reflected in visualiser at this point
#######################################################################################

data.ramped_standard = data.standard_data["Value"]
fig = data.plot_processing_overview_chart()
with open("pyplot.json", "w", encoding="utf-8") as file:
    file.write(str(fig.to_json()))
with open("pyplot.html", "w", encoding="utf-8") as file:
    file.write(str(fig.to_html()))

with open("check_table.html", "w", encoding="utf-8") as file:
    data.check_data.to_html(file)
with open("quality_table.html", "w", encoding="utf-8") as file:
    data.quality_data.to_html(file)

merger = HtmlMerger(
    [
        "pyplot.html",
        "check_table.html",
        "quality_table.html",
    ],
    encoding="utf-8",
    header=f"<h1>{data.site}</h1>\n<h2>From {data.from_date} to {data.to_date}</h2>",
)

merger.merge()
