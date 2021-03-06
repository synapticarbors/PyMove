import time

import numpy as np

from pymove.preprocessing.segmentation import by_max_dist
from pymove.utils.constants import (
    DATETIME,
    DIST_TO_PREV,
    MOVE,
    SITUATION,
    STOP,
    TRAJ_ID,
)


def create_update_datetime_in_format_cyclical(
    move_data, label_datetime=DATETIME, inplace=True
):
    """
    Converts the time data into a cyclical format.

    Parameters
    ----------
    move_data : dataframe
       The input trajectory data
    label_datetime : String, optional(datetime by default)
        Indicates the column with the data to be converted.
    inplace : boolean, optional(True by default)
        if set to true the original dataframe will be altered to contain the result of the filtering,
        otherwise a copy will be returned.


    Returns
    ------
    Returns the dataFrame with 2 aditional features: hour_sin and hour_cos.

    Notes
    -----
        https://ianlondon.github.io/blog/encoding-cyclical-features-24hour-time/
        https://www.avanwyk.com/encoding-cyclical-features-for-deep-learning/
    """
    try:
        if not inplace:
            move_df = move_data[:]
        else:
            move_df = move_data

        print("Encoding cyclical continuous features - 24-hour time")
        if label_datetime in move_data:
            hours = move_df[label_datetime].dt.hour
            move_df["hour_sin"] = np.sin(2 * np.pi * hours / 23.0)
            move_df["hour_cos"] = np.cos(2 * np.pi * hours / 23.0)
            print("...hour_sin and  hour_cos features were created...\n")

        if not inplace:
            return move_df

    except Exception as e:
        raise e


def create_or_update_move_stop_by_dist_time(
    move_data, label_id=TRAJ_ID, dist_radius=30, time_radius=900, inplace=True
):
    """
    Determines the stops and moves points of the dataframe, if these points
    already exist, they will be updated.

    Parameters
    ----------
    move_data : dataframe
       The input trajectory data
    label_id : String, optional(dic_labels["id"] by default)
         Indicates the label of the id column in the user"s dataframe.
    dist_radius : Double, optional(30 by default)
        The first step in this function is segmenting the trajectory. The segments are used to find the stop points.
        The dist_radius defines the distance used in the segmentation.
    time_radius :  Double, optional(900 by default)
        The time_radius used to determine if a segment is a stop. If the user stayed in the segment for a time
        greater than time_radius, than the segment is a stop.
    inplace : boolean, optional(True by default)
        if set to true the original dataframe will be altered to contain the result of the filtering,
        otherwise a copy will be returned.


    Returns
    ------
    Returns the dataFrame with 2 aditional features: segment_stop and stop.
        segment_stop indicates the trajectory segment to which the point belongs to.
        stop indicates if the point represents a stop.
    """
    try:
        start_time = time.time()

        if not inplace:
            move_df = move_data[:]
        else:
            move_df = move_data

        label_segment_stop = "segment_stop"
        by_max_dist(
            move_df,
            label_id=label_id,
            max_dist_between_adj_points=dist_radius,
            label_new_tid=label_segment_stop,
        )

        if label_segment_stop in move_df:
            # update dist, time and speed using segment_stop

            move_df.generate_dist_time_speed_features(
                label_id=label_segment_stop
            )

            print("Create or update stop as True or False")
            print(
                "...Creating stop features as True or False using {} to time in seconds".format(
                    time_radius
                )
            )
            move_df[STOP] = False
            move_dataagg_tid = (
                move_df.groupby(by=label_segment_stop)
                .agg({"time_to_prev": "sum"})
                .query("time_to_prev > " + str(time_radius))
                .index
            )
            idx = move_df[
                move_df[label_segment_stop].isin(move_dataagg_tid)
            ].index
            move_df.at[idx, STOP] = True
            print(move_df[STOP].value_counts())
            print(
                "\nTotal Time: {:.2f} seconds".format(
                    (time.time() - start_time)
                )
            )
            print("-----------------------------------------------------\n")

        if not inplace:
            return move_df
    except Exception as e:
        raise e


def create_update_move_and_stop_by_radius(
    move_data,
    radius=0,
    target_label=DIST_TO_PREV,
    new_label=SITUATION,
    inplace=True,
):
    """
    Finds the stops and moves points of the dataframe, if these points already
    exist, they will be updated.

    Parameters
    ----------
    move_data : dataframe
       The input trajectory data
    radius :  Double, optional(900 by default)
        The radius value is used to determine if a segment is a stop. If the value of the point in target_label is
        greater than radius, the segment is a stop, otherwise it's a move.
    target_label : String, optional(dist_to_prev by default)
        The feature used to calculate the stay points.
    new_label : String, optional(situation by default)
        Is the name of the column created to indicates if a point is a stop of a move.
    inplace : boolean, optional(True by default)
        if set to true the original dataframe will be altered to contain the result of the filtering,
        otherwise a copy will be returned.


    Returns
    ------
    Returns the dataFrame with 2 aditional features: segment_stop and new_label.
        segment_stop indicates the trajectory segment to which the point belongs to.
        new_label indicates if the point represents a stop point or a moving point.
    """
    try:
        print("\nCreating or updating features MOVE and STOPS...\n")

        if not inplace:
            move_df = move_data[:]
        else:
            move_df = move_data

        if DIST_TO_PREV not in move_df:
            move_df.generate_dist_features()

        conditions = (
            (move_df[target_label] > radius),
            (move_df[target_label] <= radius),
        )
        choices = [MOVE, STOP]

        move_df[new_label] = np.select(conditions, choices, np.nan)
        print(
            "\n....There are {} stops to this parameters\n".format(
                move_df[move_df[new_label] == STOP].shape[0]
            )
        )

        if not inplace:
            return move_df
    except Exception as e:
        raise e
