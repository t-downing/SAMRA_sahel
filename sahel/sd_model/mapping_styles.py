from sahel.models import *

stylesheet = [
    # ALL
    # nodes
    {
        "selector": "node",
        "style": {
            "content": "data(label)",
            "background-color": "data(color)",
            "width": 100,
            "height": 100,
            "border-width": 1,
            "text-valign": "top",
            "text-halign": "center",
            "text-wrap": "wrap",
            "text-max-width": 100,
            "background-opacity": 0.5,
            "background-blacken": -0.8,
        }
    },
    # edges
    {
        "selector": "edge",
        "style": {
            "curve-style": "unbundled-bezier",
            "control-point-distance": "50px",
            "arrow-scale": 1,
            "target-arrow-shape": "triangle",
        }
    },

    # GROUPS
    # nodes
    {"selector": "node.group",
     "style": {
         "color": "lightgrey",
         "font-size": 40,
         "border-width": 3,
         "border-color": "lightgrey",
         "background-color": "white",
         "z-index": 1,
     }},

    # ELEMENTS
    # nodes
    {"selector": "node.element",
     "style": {
         "font-size": 20,
         "border-width": 2,
         "z-index": 2,
     }},
    {"selector": ".IV",
     "style": {
         # rebeccapurple
         "background-color": "#66329a",
         "border-color": "#66329a",
         "color": "#66329a",
         "line-color": "#9965cd",
         "target-arrow-color": "#9965cd",
     }},
    {"selector": f".{SituationalAnalysis.SITUATIONAL_ANALYSIS}",
     "style": {
         # chocolate
         "background-color": "#d2691e",
         "border-color": "#d2691e",
         "color": "#d2691e",
         "line-color": "#e99b63",
         "target-arrow-color": "#e99b63",
     }},
    {"selector": f".{ShockStructure.SHOCK_EFFECT}, .{ShockStructure.SHOCK}",
     "style": {
         "background-color": "#F08080",
         "border-color": "crimson",
         "color": "crimson",
         "line-color": "crimson",
         "target-arrow-color": "crimson",
     }},
    {"selector": f"node.{ShockStructure.SHOCK}",
     "style": {
        # "shape": "triangle",
        "width": 150,
        "height": 150,
        "border-width": 5,
        # "text-valign": "bottom",
     }},

    # edges
    {
        "selector": "edge.element",
        "style": {
            "arrow-scale": 2,
            "control-point-distance": "-50px",
        }
    },

    # VARIABLES
    # nodes
    {"selector": "node.variable",
     "style": {
         "color": "#505050",
         "border-color": "#505050",
         "text-valign": "center",
         "z-index": 3,
     }},
    {"selector": "[sd_type = 'Stock']",
     "style": {
         "shape": "rectangle",
         "width": 150,
     }},
    {"selector": "[sd_type = 'Input']",
     "style": {
         "shape": "diamond",
     }},
    {"selector": "[sd_type = 'Household Constant']",
     "style": {
         "shape": "diamond",
     }},
    {"selector": "[sd_type = 'Constant']",
     "style": {
         "shape": "triangle",
         "text-valign": "bottom",
     }},
    {"selector": "[sd_type = 'Pulse Input']",
     "style": {
         "shape": "triangle",
         "text-valign": "bottom",
     }},
    {"selector": f"[sd_type = '{Variable.SCENARIO_CONSTANT}']",
     "style": {
         "shape": "triangle",
         "text-valign": "bottom",
     }},
    {"selector": "[!usable].variable",
     "style": {
         "background-color": "whitesmoke",
         "color": "grey",
         "border-color": "grey",
     }},

    # edges
    {"selector": "edge.variable",
     "style": {
         "target-arrow-color": "#808080",
         "line-color": "#808080",
         "width": 1,
     }},
    {"selector": "[edge_type = 'Flow']",
     "style": {
         "line-color": "#DCDCDC",
         "target-arrow-shape": "none",
         "mid-target-arrow-shape": "triangle",
         "mid-target-arrow-color": "grey",
         "width": 20,
         "arrow-scale": 0.4,
         "curve-style": "straight",
     }},
    {"selector": "[has_equation = 'no']",
     "style": {
         "line-style": "dashed"
     }},

    # SELECTED
    {"selector": ":selected",
     "style": {
         "border-color": "blue",
         "border-width": 3,
     }},

    # HIDDEN
    {
        "selector": ".hidden",
        "style": {
            "display": "none"
        }
    }
]

fieldvalue2color = {
    "status": {
        SituationalAnalysis.SA_STATUS_GOOD: {
            "body": "green",
            "border": "green",
            "ring": "green",
        },
        SituationalAnalysis.SA_STATUS_OK: {
            "body": "yellow",
            "border": "yellow",
            "ring": "yellow",
        },
        SituationalAnalysis.SA_STATUS_BAD: {
            "body": "red",
            "border": "red",
            "ring": "red",
        },
    },
    "trend": {
        SituationalAnalysis.SA_TREND_IMPROVING: {
            "body": "green",
            "border": "green",
            "ring": "green",
        },
        SituationalAnalysis.SA_TREND_STAGNANT: {
            "body": "yellow",
            "border": "yellow",
            "ring": "yellow",
        },
        SituationalAnalysis.SA_TREND_WORSENING: {
            "body": "red",
            "border": "red",
            "ring": "red",
        }
    },
    "resilience": {
        SituationalAnalysis.SA_RES_HIGH: {
            "body": "green",
            "border": "green",
            "ring": "green",
        },
        SituationalAnalysis.SA_RES_MED: {
            "body": "yellow",
            "border": "yellow",
            "ring": "yellow",
        },
        SituationalAnalysis.SA_RES_LOW: {
            "body": "red",
            "border": "red",
            "ring": "red",
        }
    },
}

partname2cytokey = {
    "body": "background-color",
    "border": "border-color",
}