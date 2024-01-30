import model
import candles
import logging

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io

import pandas as pd

logging.basicConfig(level=logging.INFO)

def render(_df,
           _predicted_data,
           cutoff_delta: str,
           fname=None) -> io.BytesIO:
    """
    Render a graph with known data and predicted data.
    @param _df: pd.DataFrame : the known data
    @param _predicted_data: pd.DataFrame : the predicted data
    @param cutoff_delta: str : the cutoff delta to use
    @param fname: str : the filename to save the graph to
    """

    # copies
    df = _df
    predicted_data = _predicted_data

    # cutoff
    if type(df['ts_utc'].iloc[-1]) == str:
        df['ts_utc'] = pd.to_datetime(df['ts_utc'])

    cutoff_time = df.iloc[-1]['ts_utc'] - pd.to_timedelta(cutoff_delta)

    df = df[df['ts_utc'] > cutoff_time]

    # plot with plt (known data)
    plt.plot(df['ts_utc'], df['c'], color='black', label='Known Data')

    # plot with plt (prediction)
    plt.plot(predicted_data['ds'], predicted_data['yhat'], color='blue', label='Predicted Values')

    plt.plot(predicted_data['ds'], predicted_data['yhat_upper'], color='green', linestyle='dashed', label='Upper Bound')
    plt.plot(predicted_data['ds'], predicted_data['yhat_lower'], color='red', linestyle='dashed', label='Lower Bound')

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M')) 
    plt.xticks(rotation=45, ha='right')

    plt.xlabel('Time')
    plt.ylabel('Closed Price')
    #plt.title('Prognosis')

    if fname:
        plt.savefig(fname)

    buffer = io.BytesIO()
    plt.savefig(buffer, format='jpg')
    buffer.seek(0)
    return buffer


def main(pair_address: str):
    # open candles.csv as dataframe
    df = pd.read_csv("candles.csv")
    predicted_data = model.predict(df, 20, "15min", "ts_utc", "c")
    render(df, predicted_data, "72 hours", "render.png")

    if False:
        pair_universe = candles.get_pair_universe()
        pair_id = candles.get_uniswap_pair_id(pair_universe,
                                            pair_address)

        df = candles.get_candles(pair_id, "15m")
        logging.info("Got candles")

        # add a column with ts in utc timezone
        #df['ts_utc'] = pd.to_datetime(df['ts'], unit='s')

        predicted_data = model.predict(df, 60, "15min", "ts_utc", "c")
        print(predicted_data.head())

        # render
        render(df, predicted_data, "200 hours", "rendar.png")
    """
    # cutoff
    cutoff_delta = "200 hours"
    cutoff_time = df.iloc[-1]['ts_utc'] - pd.to_timedelta(cutoff_delta)

    df = df[df['ts_utc'] > cutoff_time]

    # plot with plt (known data)
    plt.plot(df['ts_utc'], df['c'], color='black', label='Known Data')

    # plot with plt (prediction)
    plt.plot(predicted_data['ds'], predicted_data['yhat'], color='blue', label='Predicted Values')

    plt.plot(predicted_data['ds'], predicted_data['yhat_upper'], color='green', linestyle='dashed', label='Upper Bound')
    plt.plot(predicted_data['ds'], predicted_data['yhat_lower'], color='red', linestyle='dashed', label='Lower Bound')

    plt.xlabel('Timestamp')
    plt.ylabel('Closed Price')
    plt.title('Known Data and Predicted Values')

    plt.legend()
    plt.savefig('graph_newest.png')
    """
