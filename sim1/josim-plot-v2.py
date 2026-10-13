#!/usr/bin/env python

# Import relevant packages
import os
import math
import sys
import argparse

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import plotly

# ============================================================
# Function that sets the Y-axis title relevant to the data
# ============================================================
def y_axis_title(figLabel):
    label = str(figLabel).strip().upper()
    if label.startswith('V'):
        return "Vol(V)"
    elif label.startswith('I'):
        return "Cur(A)"
    elif label.startswith('P'):
        # Phase data has already been divided by 2*pi
        return "N(2π)"
    else:
        return "No"

# ============================================================
# Convert JoSIM phase data
#
# JoSIM P(...) output:
#     phase in radians
#
# Converted data:
#     phase / (2*pi)
#
# Therefore:
#     0       -> 0
#     2*pi    -> 1
#     4*pi    -> 2
#     6*pi    -> 3
#
# This remains continuous; no rounding is performed.
# ============================================================
def convert_phase_data(df):
    for col in df.columns[1:]:
        col_name = str(col).strip()
        # JoSIM phase columns normally begin with P(...)
        if col_name.upper().startswith('P'):
            df[col] = (
                pd.to_numeric(df[col], errors='coerce')
                / (2.0 * math.pi)
            )
    return df

# ============================================================
# Return a grid of plots
# ============================================================
def grid_layout(df, subset):
    plots = df.columns[1:].tolist() if subset is None else subset
    rows = math.ceil(len(plots) / 2)
    fig = make_subplots(
        rows=rows,
        cols=2 if len(plots) > 1 else 1,
        subplot_titles=plots,
        horizontal_spacing=0.075,
        vertical_spacing=0.2 / rows,
        x_title='Time (seconds)'
    )
    # Add the traces
    for i in range(0, len(plots)):
        col = 1 if (i % 2 == 0) else 2
        row = int(math.floor(i / 2)) + 1
        fig.add_trace(
            go.Scatter(
                x=df.iloc[:, 0],
                y=df.loc[:, plots[i]],
                mode='lines',
                name=plots[i]
            ),
            row=row,
            col=col
        )
        fig.layout.annotations[i].x = (
            0.45 if (i % 2 == 0) else 0.985
        )
        if i == 0:
            fig['layout']['yaxis']['title'] = \
                y_axis_title(plots[i])
        else:
            fig['layout']['yaxis' + str(i + 1)]['title'] = \
                y_axis_title(plots[i])
    return fig

# ============================================================
# Return a square of plots
# ============================================================
def square_layout(df, subset):
    plots = df.columns[1:].tolist() if subset is None else subset
    square = math.sqrt(len(plots))
    row = int(round(square))
    col = int(math.ceil(square))
    fig = make_subplots(
        rows=row,
        cols=col,
        subplot_titles=plots,
        horizontal_spacing=(0.25 / row),
        vertical_spacing=(0.25 / col),
        x_title='Time (seconds)'
    )
    row_counter = 1
    col_counter = 1
    # Add the traces
    for i in range(0, len(plots)):
        if i >= row_counter * math.ceil(square):
            row_counter += 1
            col_counter = 1
        col = col_counter
        row = row_counter
        fig.add_trace(
            go.Scatter(
                x=df.iloc[:, 0],
                y=df.loc[:, plots[i]],
                mode='lines',
                name=plots[i]
            ),
            row=row,
            col=col
        )
        an_pos = 1 / math.ceil(square)
        fig.layout.annotations[i].x = \
            an_pos * col_counter - 0.5 * an_pos
        fig.update_yaxes(
            row=row_counter,
            col=col_counter,
            title_standoff=0,
            ticks=""
        )
        if i == 0:
            fig['layout']['yaxis']['title'] = \
                y_axis_title(plots[i])
        else:
            fig['layout']['yaxis' + str(i + 1)]['title'] = \
                y_axis_title(plots[i])
        col_counter += 1
    return fig

# ============================================================
# Return a stack of plots
# ============================================================
def stacked_layout(df, subset):
    plots = df.columns[1:].tolist() if subset is None else subset
    fig = make_subplots(
        rows=len(plots),
        cols=1,
        subplot_titles=plots,
        vertical_spacing=0.2 / math.ceil(len(plots) / 2),
        x_title='Time (seconds)'
    )
    # Add the traces
    for i in range(0, len(plots)):
        fig.add_trace(
            go.Scatter(
                x=df.iloc[:, 0],
                y=df.loc[:, plots[i]],
                mode='lines',
                name=plots[i]
            ),
            row=i + 1,
            col=1
        )
        fig.layout.annotations[i].x = 1.1
        if i == 0:
            fig['layout']['yaxis']['title'] = \
                y_axis_title(plots[i])
        else:
            fig['layout']['yaxis' + str(i + 1)]['title'] = \
                y_axis_title(plots[i])
    return fig

# ============================================================
# Separate and combine like plots
# ============================================================
def seperate_combined_layout(df, subset):
    plots = df.columns[1:].tolist() if subset is None else subset
    V = []
    P = []
    I = []
    U = []
    for i in range(0, len(plots)):
        label = str(plots[i]).strip().upper()
        if label.startswith('V'):
            V.append(i)
        elif label.startswith('I'):
            I.append(i)
        elif label.startswith('P'):
            P.append(i)
        else:
            U.append(i)
    fig_count = 0
    if len(V) != 0:
        fig_count += 1
    if len(P) != 0:
        fig_count += 1
    if len(I) != 0:
        fig_count += 1
    if len(U) != 0:
        fig_count += 1
    fig = make_subplots(
        rows=fig_count,
        cols=1,
        vertical_spacing=0.2 / math.ceil(fig_count / 2),
        x_title='Time (seconds)'
    )
    # Add the traces
    fig_count = 0

    # --------------------------------------------------------
    # Unknown / other signals
    # --------------------------------------------------------
    if len(U) != 0:
        fig_count += 1
        for i in U:
            fig.add_trace(
                go.Scatter(
                    x=df.iloc[:, 0],
                    y=df.loc[:, plots[i]],
                    mode='lines',
                    name=plots[i]
                ),
                row=fig_count,
                col=1
            )
        fig['layout']['yaxis' + str(fig_count)]['title'] = \
            y_axis_title(plots[U[0]])

    # --------------------------------------------------------
    # Voltage signals
    # --------------------------------------------------------
    if len(V) != 0:
        fig_count += 1
        for i in V:
            fig.add_trace(
                go.Scatter(
                    x=df.iloc[:, 0],
                    y=df.loc[:, plots[i]],
                    mode='lines',
                    name=plots[i]
                ),
                row=fig_count,
                col=1
            )
        fig['layout']['yaxis' + str(fig_count)]['title'] = \
            y_axis_title(plots[V[0]])

    # --------------------------------------------------------
    # Phase signals
    #
    # These have already been converted:
    #     phase(rad) / (2*pi)
    # --------------------------------------------------------
    if len(P) != 0:
        fig_count += 1
        for i in P:
            fig.add_trace(
                go.Scatter(
                    x=df.iloc[:, 0],
                    y=df.loc[:, plots[i]],
                    mode='lines',
                    name=plots[i]
                ),
                row=fig_count,
                col=1
            )
        fig['layout']['yaxis' + str(fig_count)]['title'] = \
            y_axis_title(plots[P[0]])

    # --------------------------------------------------------
    # Current signals
    # --------------------------------------------------------
    if len(I) != 0:
        fig_count += 1
        for i in I:
            fig.add_trace(
                go.Scatter(
                    x=df.iloc[:, 0],
                    y=df.loc[:, plots[i]],
                    mode='lines',
                    name=plots[i]
                ),
                row=fig_count,
                col=1
            )
        fig['layout']['yaxis' + str(fig_count)]['title'] = \
            y_axis_title(plots[I[0]])
    return fig


# ============================================================
# Combine all the plots
# ============================================================
def combined_layout(df, subset):
    plots = df.columns[1:].tolist() if subset is None else subset
    fig = go.Figure()
    # Add the traces
    for i in range(0, len(plots)):
        fig.add_trace(
            go.Scatter(
                x=df.iloc[:, 0],
                y=df.loc[:, plots[i]],
                mode='lines',
                name=plots[i]
            )
        )
    return fig


# ============================================================
# Main function
# ============================================================
def main():
    # Version info
    vers = \
        "JoSIM Trace Plotting Script - 1.4 - CSV/DAT plotting script"
    # Initiate the parser
    parser = argparse.ArgumentParser(
        description=vers
    )
    # Add possible parser arguments
    parser.add_argument(
        "input",
        help="the CSV input file"
    )
    parser.add_argument(
        "-o",
        "--output",
        help=(
            "the output file name with supported extensions: "
            "png, jpeg, webp, svg, eps, pdf"
        )
    )
    parser.add_argument(
        "-d",
        "--dimensions",
        help="the dimensions of the output file"
    )
    parser.add_argument(
        "-x",
        "--html",
        help="save the output as an html file for later viewing"
    )
    parser.add_argument(
        "-t",
        "--type",
        help=(
            "type of plot: grid, stacked, combined, "
            "square, sep_comb. Default: grid"
        ),
        default="grid"
    )
    parser.add_argument(
        "-s",
        "--subset",
        nargs='+',
        help=(
            "subset of traces to plot. specify list of column "
            "names (as shown in csv file header), ie. "
            "\"V(1)\" \"V(2)\". Default: None"
        )
    )
    parser.add_argument(
        "-c",
        "--color",
        help=(
            "set the output plot color scheme to one of the "
            "following: light, dark, presentation. "
            "Default: dark"
        ),
        default='dark'
    )
    parser.add_argument(
        "-w",
        "--title",
        help="set plot title to the provided string"
    )
    parser.add_argument(
        "-V",
        "--version",
        action='version',
        help="show script version",
        version=vers
    )
    # Read arguments from the command line
    args = parser.parse_args()

    # List of possible output formats
    outformats = [
        ".png",
        ".jpeg",
        ".webp",
        ".svg",
        ".eps",
        ".pdf"
    ]

    # ========================================================
    # Read CSV / DAT
    # ========================================================
    extension = os.path.splitext(args.input)[1].lower()
    if extension == ".csv":
        df = pd.read_csv(
            args.input,
            sep=','
        )
    elif extension == ".dat":

        df = pd.read_csv(
            args.input,
            sep=r'\s+'
        )
    else:
        print(
            "Invalid input file specified: "
            + args.input
        )
        print(
            "Please provide either .csv "
            "(comma separated) or .dat "
            "(space separated) file"
        )
        sys.exit()

    # ========================================================
    # Convert JoSIM phase data
    #
    # All columns beginning with P are assumed to be
    # JoSIM phase output:
    #
    #     P(BJ1)
    #     P(BJ1|XBQ)
    #     P(B01.X01)
    #
    # Original unit:
    #     rad
    #
    # Converted unit:
    #     phase / (2*pi)
    #
    # Example:
    #
    #     0          -> 0
    #     6.283185   -> 1
    #     12.566371  -> 2
    #
    # ========================================================
    df = convert_phase_data(df)

    # ========================================================
    # Determine the plot layout
    # ========================================================
    if args.type == "grid":
        fig = grid_layout(
            df,
            args.subset
        )
    elif args.type == "stacked":
        fig = stacked_layout(
            df,
            args.subset
        )
    elif args.type == "combined":
        fig = combined_layout(
            df,
            args.subset
        )
    elif args.type == "square":
        fig = square_layout(
            df,
            args.subset
        )
    elif args.type == "sep_comb":
        fig = seperate_combined_layout(
            df,
            args.subset
        )
    else:
        print(
            "Invalid plot type specified: "
            + args.type
        )
        print(
            "Please provide either grid, stacked, "
            "combined, square or sep_comb as type"
        )
        sys.exit()


    # ========================================================
    # Determine the theme to plot with
    # ========================================================
    if args.color == 'light':
        template = 'plotly_white'
    elif args.color == 'dark':
        template = 'plotly_dark'
    elif args.color == 'presentation':
        template = 'presentation'
    else:
        print(
            "Invalid plot color specified: "
            + args.color
        )
        print(
            "Please provide either light, dark "
            "or presentation as color theme"
        )
        sys.exit()

    # ========================================================
    # Set the title of the plot
    # ========================================================
    if args.title is None:
        title = os.path.splitext(
            os.path.basename(args.input)
        )[0]
    else:
        title = args.title

    # ========================================================
    # Update the layout based on the settings
    # ========================================================
    fig.update_layout(
        title=title,
        title_font_size=20,
        template=template,
        showlegend=False,
        margin=dict(
            l=50,   # 左边距
            r=150,  # 右边距
            t=100,  # 上边距
            b=50    # 下边距
        )
    )
    fig.update_annotations(
        font=dict(
            size=15
        )
    )

    # ========================================================
    # Set the mode bar buttons
    # ========================================================
    config = dict({
        'scrollZoom': True,
        'displaylogo': False,
        'toImageButtonOptions': {
            'format': 'svg',
            'filename': title,
            'height': None,
            'width': None
        },
        'modeBarButtonsToAdd': [
            'toggleSpikelines',
            'hovercompare',
            'v1hovermode'
        ]
    })

    # ========================================================
    # Determine whether to show the plot
    # or dump to file
    # ========================================================
    if args.output is None and args.html is None:
        fig.show(
            config=config
        )
    elif args.html is not None and args.output is None:
        fig.write_html(
            args.html
        )
    elif (
        args.html is None
        and args.output is not None
        and os.path.splitext(args.output)[1].lower()
        in outformats
    ):
        if args.dimensions is None:
            print(
                "Please specify image dimensions "
                "using -d, for example: "
                "-d 1920x1080"
            )
            sys.exit()
        w, h = args.dimensions.lower().split("x")
        fig.write_image(
            args.output,
            width=int(w),
            height=int(h)
        )
    else:
        print(
            "Unknown file format for output file specified."
        )
        print(
            "Please use: png, jpeg, webp, "
            "svg, eps or pdf"
        )

# ============================================================
# Run
# ============================================================
if __name__ == '__main__':
    main()