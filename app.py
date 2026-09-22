from dash import (
    Dash,
    html,
    dcc,
    Input,
    Output,
    State,
    ctx,
)

from dash.dependencies import ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from services.player import play_media

from database import (
    create_database,
    get_movies_with_metadata,
    get_media_by_id,
    toggle_favorite,
    record_play,
    get_most_watched,
    get_recently_watched,
    get_shows_with_metadata,
    get_show_by_id,
    get_show_episodes,
)


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

create_database()


# --------------------------------------------------
# APP
# --------------------------------------------------

app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
    ],
)

app.title = "My Media Library"


# --------------------------------------------------
# MOVIE CARDS
# --------------------------------------------------

def build_movie_card(movie):

    poster = movie["poster_url"]

    if not poster:
        poster = (
            "https://placehold.co/"
            "500x750?text=No+Poster"
        )

    year = movie["year"] or "Unknown"

    rating = movie["tmdb_rating"]

    if rating:
        rating_text = f"★ {rating:.1f}"
    else:
        rating_text = "No rating"

    card = dbc.Card(
        [
            dbc.CardImg(
                src=poster,
                top=True,
                className="movie-poster",
            ),

            dbc.CardBody(
                [
                    html.H5(
                        movie["title"],
                        className="movie-title",
                    ),

                    html.Div(
                        [
                            html.Span(
                                str(year),
                                className="me-3",
                            ),

                            html.Span(
                                rating_text,
                            ),
                        ],
                        className="text-muted",
                    ),
                ]
            ),
        ],
        className="movie-card h-100",
    )

    return html.Div(
        card,
        id={
            "type": "movie-card",
            "index": movie["id"],
        },
        n_clicks=0,
        className="movie-card-clickable h-100",
    )


def build_movie_grid(movies):

    return [
        dbc.Col(
            build_movie_card(movie),
            xs=6,
            sm=4,
            md=3,
            lg=2,
            className="mb-4",
        )
        for movie in movies
    ]


def build_movie_row(movies):

    return html.Div(
        [
            html.Div(
                build_movie_card(movie),
                className="movie-row-item",
            )
            for movie in movies
        ],
        className="movie-row",
    )


def build_movie_section(
    title,
    movies,
    empty_message=None,
):

    if not movies:

        if empty_message:

            return html.Div(
                [
                    html.H3(
                        title,
                        className="mb-3",
                    ),

                    html.P(
                        empty_message,
                        className="text-muted",
                    ),
                ]
            )

        return html.Div()

    return html.Div(
        [
            html.H3(
                title,
                className="mb-3",
            ),

            build_movie_row(
                movies
            ),
        ],
        className="mb-5",
    )


# --------------------------------------------------
# TV SHOW CARDS
# --------------------------------------------------

def build_show_card(show):

    poster = show["poster_url"]

    if not poster:
        poster = (
            "https://placehold.co/"
            "500x750?text=No+Poster"
        )

    year = show["year"] or "Unknown"

    rating = show["tmdb_rating"]

    if rating:
        rating_text = f"★ {rating:.1f}"
    else:
        rating_text = "No rating"

    episode_count = show["episode_count"]

    if episode_count == 1:
        episode_text = "1 episode"
    else:
        episode_text = (
            f"{episode_count} episodes"
        )

    card = dbc.Card(
        [
            dbc.CardImg(
                src=poster,
                top=True,
                className="movie-poster",
            ),

            dbc.CardBody(
                [
                    html.H5(
                        show["title"],
                        className="movie-title",
                    ),

                    html.Div(
                        [
                            html.Span(
                                str(year),
                                className="me-3",
                            ),

                            html.Span(
                                rating_text,
                            ),
                        ],
                        className="text-muted",
                    ),

                    html.Div(
                        episode_text,
                        className="text-muted mt-1",
                    ),
                ]
            ),
        ],
        className="movie-card h-100",
    )

    return html.Div(
        card,
        id={
            "type": "show-card",
            "index": show["id"],
        },
        n_clicks=0,
        className="movie-card-clickable h-100",
    )


def build_show_grid(shows):

    return [
        dbc.Col(
            build_show_card(show),
            xs=6,
            sm=4,
            md=3,
            lg=2,
            className="mb-4",
        )
        for show in shows
    ]


# --------------------------------------------------
# TV EPISODES
# --------------------------------------------------

def build_episode_item(episode):

    season = episode["season_number"]
    number = episode["episode_number"]

    if (
        season is not None
        and number is not None
    ):
        episode_code = (
            f"S{season:02d}E{number:02d}"
        )

    elif number is not None:
        episode_code = (
            f"E{number:02d}"
        )

    else:
        episode_code = "Episode"

    title = (
        episode["episode_title"]
        or episode["filename"]
    )

    still = episode["still_url"]

    content = []

    if still:
        content.append(
            html.Img(
                src=still,
                className="episode-still",
            )
        )

    content.append(
        html.Div(
            [
                html.Div(
                    [
                        html.Strong(
                            episode_code
                        ),

                        html.Span(
                            f" — {title}"
                        ),
                    ]
                ),

                html.P(
                    episode["overview"]
                    or "No description available.",
                    className=(
                        "text-muted "
                        "episode-overview"
                    ),
                ),

                html.Small(
                    episode["filename"],
                    className="text-muted",
                ),

                html.Br(),

                dbc.Button(
                    "▶ Play",
                    id={
                        "type":
                            "episode-play-button",
                        "index":
                            episode["media_id"],
                    },
                    color="primary",
                    size="sm",
                    className="mt-3",
                ),
            ],
            className="episode-info",
        )
    )

    return html.Div(
        content,
        className="episode-item",
    )


def build_season_sections(episodes):

    seasons = {}

    for episode in episodes:

        season_number = (
            episode["season_number"]
        )

        if season_number not in seasons:
            seasons[season_number] = []

        seasons[season_number].append(
            episode
        )

    sections = []

    for (
        season_number,
        season_episodes,
    ) in seasons.items():

        if season_number is None:
            season_title = "Other"

        elif season_number == 0:
            season_title = "Specials"

        else:
            season_title = (
                f"Season {season_number}"
            )

        sections.append(
            html.Div(
                [
                    html.H4(
                        season_title,
                        className="mt-4 mb-3",
                    ),

                    html.Div(
                        [
                            build_episode_item(
                                episode
                            )
                            for episode
                            in season_episodes
                        ]
                    ),
                ]
            )
        )

    return sections


# --------------------------------------------------
# LAYOUT
# --------------------------------------------------

def build_layout():

    shows = get_shows_with_metadata()
    movies = get_movies_with_metadata()

    favorites = [
        movie
        for movie in movies
        if movie["favorite"]
    ]

    recently_watched = (
        get_recently_watched(
            limit=12
        )
    )

    most_watched = (
        get_most_watched(
            limit=12
        )
    )

    return dbc.Container(
        [
            # --------------------------------------
            # HEADER
            # --------------------------------------

            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H1(
                                "My Media Library",
                                className="mt-4",
                            ),

                            html.P(
                                (
                                    f"{len(movies)} movies"
                                    f" • "
                                    f"{len(shows)} TV shows"
                                ),
                                id="movie-count",
                                className="text-muted",
                            ),
                        ]
                    )
                ]
            ),

            # --------------------------------------
            # SEARCH
            # --------------------------------------

            dbc.Row(
                [
                    dbc.Col(
                        [
                            dcc.Input(
                                id="movie-search",
                                type="text",
                                placeholder=(
                                    "Search your "
                                    "library..."
                                ),
                                className="form-control",
                                debounce=False,
                            )
                        ],
                        md=6,
                    )
                ],
                className="mb-4",
            ),

            # --------------------------------------
            # NAVIGATION
            # --------------------------------------

            dbc.Row(
                [
                    dbc.Col(
                        dbc.ButtonGroup(
                            [
                                dbc.Button(
                                    "Home",
                                    id="home-button",
                                    color="primary",
                                ),

                                dbc.Button(
                                    "Movies",
                                    id="movies-button",
                                    color="secondary",
                                ),

                                dbc.Button(
                                    "TV Shows",
                                    id="shows-button",
                                    color="secondary",
                                ),
                            ]
                        )
                    )
                ],
                className="mb-4",
            ),

            # --------------------------------------
            # HOME VIEW
            # --------------------------------------

            html.Div(
                [
                    html.Div(
                        build_movie_section(
                            "♥ My Favorites",
                            favorites,
                            (
                                "Favorite a movie "
                                "and it will appear "
                                "here."
                            ),
                        ),
                        id="favorites-section",
                    ),

                    html.Div(
                        build_movie_section(
                            "Recently Watched",
                            recently_watched,
                        ),
                        id=(
                            "recently-watched-"
                            "section"
                        ),
                    ),

                    html.Div(
                        build_movie_section(
                            "Most Watched",
                            most_watched,
                        ),
                        id=(
                            "most-watched-"
                            "section"
                        ),
                    ),
                ],
                id="home-view",
            ),

            # --------------------------------------
            # MOVIES VIEW
            # --------------------------------------

            html.Div(
                [
                    html.H3(
                        "All Movies",
                        className="mb-3",
                    ),

                    dbc.Row(
                        build_movie_grid(
                            movies
                        ),
                        id="movie-grid",
                        className="g-3",
                    ),
                ],
                id="movies-view",
                style={
                    "display": "none"
                },
            ),

            # --------------------------------------
            # TV SHOWS VIEW
            # --------------------------------------

            html.Div(
                [
                    html.H3(
                        "TV Shows",
                        className="mb-3",
                    ),

                    html.P(
                        f"{len(shows)} shows",
                        className="text-muted",
                    ),

                    dbc.Row(
                        build_show_grid(
                            shows
                        ),
                        id="show-grid",
                        className="g-3",
                    ),
                ],
                id="shows-view",
                style={
                    "display": "none"
                },
            ),

            # --------------------------------------
            # STORES
            # --------------------------------------

            dcc.Store(
                id="selected-movie-id"
            ),

            dcc.Store(
                id="selected-show-id"
            ),

            # --------------------------------------
            # MOVIE MODAL
            # --------------------------------------

            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle(
                            id=(
                                "movie-modal-"
                                "title"
                            )
                        ),
                        close_button=True,
                    ),

                    html.Div(
                        id="playback-message",
                        className="px-3 pb-2",
                    ),

                    dbc.ModalBody(
                        id="movie-modal-body"
                    ),

                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "♡ Favorite",
                                id=(
                                    "favorite-"
                                    "button"
                                ),
                                color="secondary",
                                className="me-2",
                            ),

                            dbc.Button(
                                "▶ Play",
                                id="play-button",
                                color="primary",
                            ),
                        ]
                    ),
                ],
                id="movie-modal",
                size="lg",
                is_open=False,
            ),

            # --------------------------------------
            # TV SHOW MODAL
            # --------------------------------------

            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle(
                            id="show-modal-title"
                        ),
                        close_button=True,
                    ),

                    html.Div(
                        id=(
                            "episode-playback-"
                            "message"
                        ),
                        className="px-3 pb-2",
                    ),

                    dbc.ModalBody(
                        id="show-modal-body"
                    ),
                ],
                id="show-modal",
                size="xl",
                is_open=False,
            ),
        ],
        fluid=True,
    )


app.layout = build_layout()


# --------------------------------------------------
# NAVIGATION
# --------------------------------------------------
@app.callback(
    Output("home-view", "style"),
    Output("movies-view", "style"),
    Output("shows-view", "style"),

    Output("home-button", "color"),
    Output("movies-button", "color"),
    Output("shows-button", "color"),

    Input("home-button", "n_clicks"),
    Input("movies-button", "n_clicks"),
    Input("shows-button", "n_clicks"),
)
def switch_library_view(
    home_clicks,
    movie_clicks,
    show_clicks,
):

    triggered = ctx.triggered_id

    hidden = {
        "display": "none"
    }

    visible = {
        "display": "block"
    }

    if triggered == "movies-button":
        return (
            hidden,
            visible,
            hidden,
            "secondary",
            "primary",
            "secondary",
        )

    if triggered == "shows-button":
        return (
            hidden,
            hidden,
            visible,
            "secondary",
            "secondary",
            "primary",
        )

    return (
        visible,
        hidden,
        hidden,
        "primary",
        "secondary",
        "secondary",
    )
# --------------------------------------------------
# MOVIE SEARCH
# --------------------------------------------------

@app.callback(
    Output(
        "movie-grid",
        "children",
    ),
    Output(
        "movie-count",
        "children",
    ),
    Input(
        "movie-search",
        "value",
    ),
)
def search_movies(search_text):

    movies = get_movies_with_metadata()
    shows = get_shows_with_metadata()

    if search_text:

        search_text = (
            search_text
            .strip()
            .lower()
        )

        movies = [
            movie
            for movie in movies
            if search_text
            in movie["title"].lower()
        ]

    movie_count = len(movies)

    if movie_count == 1:
        movie_text = "1 movie"
    else:
        movie_text = (
            f"{movie_count} movies"
        )

    show_count = len(shows)

    if show_count == 1:
        show_text = "1 TV show"
    else:
        show_text = (
            f"{show_count} TV shows"
        )

    count_text = (
        f"{movie_text} • {show_text}"
    )

    return (
        build_movie_grid(movies),
        count_text,
    )


# --------------------------------------------------
# OPEN MOVIE DETAILS
# --------------------------------------------------

@app.callback(
    Output(
        "movie-modal",
        "is_open",
    ),
    Output(
        "movie-modal-title",
        "children",
    ),
    Output(
        "movie-modal-body",
        "children",
    ),
    Output(
        "selected-movie-id",
        "data",
    ),
    Output(
        "favorite-button",
        "children",
    ),

    Input(
        {
            "type": "movie-card",
            "index": ALL,
        },
        "n_clicks",
    ),

    State(
        "movie-modal",
        "is_open",
    ),

    prevent_initial_call=True,
)
def open_movie_details(
    clicks,
    is_open,
):

    if not ctx.triggered_id:

        return (
            is_open,
            "",
            "",
            None,
            "♡ Favorite",
        )

    triggered_value = (
        ctx.triggered[0]["value"]
    )

    if not triggered_value:

        return (
            is_open,
            "",
            "",
            None,
            "♡ Favorite",
        )

    media_id = (
        ctx.triggered_id["index"]
    )

    movie = get_media_by_id(
        media_id
    )

    if not movie:

        return (
            False,
            "",
            "",
            None,
            "♡ Favorite",
        )

    poster = movie["poster_url"]

    year = (
        movie["year"]
        or "Unknown"
    )

    runtime = movie["runtime"]
    genres = movie["genres"]
    rating = movie["tmdb_rating"]
    overview = movie["overview"]

    info = [
        str(year)
    ]

    if runtime:
        info.append(
            f"{runtime} min"
        )

    if genres:
        info.append(
            genres
        )

    details = " • ".join(
        info
    )

    if rating:
        rating_text = (
            f"★ {rating:.1f} / 10"
        )
    else:
        rating_text = (
            "No rating"
        )

    if movie["favorite"]:
        favorite_text = (
            "♥ Favorited"
        )
    else:
        favorite_text = (
            "♡ Favorite"
        )

    body = dbc.Row(
        [
            dbc.Col(
                dbc.CardImg(
                    src=poster,
                    className=(
                        "details-poster"
                    ),
                ),
                md=4,
            ),

            dbc.Col(
                [
                    html.H5(
                        details
                    ),

                    html.P(
                        rating_text,
                        className=(
                            "text-warning"
                        ),
                    ),

                    html.Hr(),

                    html.P(
                        overview
                        or (
                            "No description "
                            "available."
                        )
                    ),

                    html.Hr(),

                    html.P(
                        (
                            f"Watched "
                            f"{movie['play_count']} "
                            f"times"
                        ),
                        className=(
                            "text-muted"
                        ),
                    ),
                ],
                md=8,
            ),
        ],
        className="g-4",
    )

    return (
        True,
        movie["title"],
        body,
        media_id,
        favorite_text,
    )


# --------------------------------------------------
# FAVORITE MOVIE
# --------------------------------------------------

@app.callback(
    Output(
        "favorite-button",
        "children",
        allow_duplicate=True,
    ),

    Output(
        "favorites-section",
        "children",
    ),

    Input(
        "favorite-button",
        "n_clicks",
    ),

    State(
        "selected-movie-id",
        "data",
    ),

    prevent_initial_call=True,
)
def favorite_movie(
    n_clicks,
    media_id,
):

    if not media_id:

        movies = (
            get_movies_with_metadata()
        )

        favorites = [
            movie
            for movie in movies
            if movie["favorite"]
        ]

        return (
            "♡ Favorite",

            build_movie_section(
                "♥ My Favorites",
                favorites,
                (
                    "Favorite a movie and "
                    "it will appear here."
                ),
            ),
        )

    is_favorite = (
        toggle_favorite(
            media_id
        )
    )

    if is_favorite:
        button_text = (
            "♥ Favorited"
        )
    else:
        button_text = (
            "♡ Favorite"
        )

    movies = (
        get_movies_with_metadata()
    )

    favorites = [
        movie
        for movie in movies
        if movie["favorite"]
    ]

    favorites_section = (
        build_movie_section(
            "♥ My Favorites",
            favorites,
            (
                "Favorite a movie and "
                "it will appear here."
            ),
        )
    )

    return (
        button_text,
        favorites_section,
    )


# --------------------------------------------------
# PLAY MOVIE
# --------------------------------------------------

@app.callback(
    Output(
        "playback-message",
        "children",
    ),

    Output(
        "recently-watched-section",
        "children",
    ),

    Output(
        "most-watched-section",
        "children",
    ),

    Input(
        "play-button",
        "n_clicks",
    ),

    State(
        "selected-movie-id",
        "data",
    ),

    prevent_initial_call=True,
)
def play_selected_movie(
    n_clicks,
    media_id,
):

    if not media_id:
        raise PreventUpdate

    movie = get_media_by_id(
        media_id
    )

    if not movie:
        raise PreventUpdate

    result = play_media(
        movie["path"]
    )

    if not result["success"]:

        return (
            dbc.Alert(
                result["message"],
                color="danger",
            ),

            build_movie_section(
                "Recently Watched",
                get_recently_watched(12),
            ),

            build_movie_section(
                "Most Watched",
                get_most_watched(12),
            ),
        )

    record_play(
        media_id
    )

    recently_watched = (
        get_recently_watched(12)
    )

    most_watched = (
        get_most_watched(12)
    )

    return (
        dbc.Alert(
            "Playback started.",
            color="success",
            duration=3000,
        ),

        build_movie_section(
            "Recently Watched",
            recently_watched,
        ),

        build_movie_section(
            "Most Watched",
            most_watched,
        ),
    )


# --------------------------------------------------
# OPEN TV SHOW
# --------------------------------------------------

@app.callback(
    Output(
        "show-modal",
        "is_open",
    ),
    Output(
        "show-modal-title",
        "children",
    ),
    Output(
        "show-modal-body",
        "children",
    ),
    Output(
        "selected-show-id",
        "data",
    ),

    Input(
        {
            "type": "show-card",
            "index": ALL,
        },
        "n_clicks",
    ),

    State(
        "show-modal",
        "is_open",
    ),

    prevent_initial_call=True,
)
def open_show_details(
    clicks,
    is_open,
):

    if not ctx.triggered_id:
        raise PreventUpdate

    triggered_value = (
        ctx.triggered[0]["value"]
    )

    if not triggered_value:
        raise PreventUpdate

    show_id = (
        ctx.triggered_id["index"]
    )

    show = get_show_by_id(
        show_id
    )

    if not show:
        raise PreventUpdate

    episodes = (
        get_show_episodes(
            show_id
        )
    )

    poster = show["poster_url"]
    overview = show["overview"]

    year = (
        show["year"]
        or "Unknown"
    )

    rating = show["tmdb_rating"]

    if rating:
        rating_text = (
            f"★ {rating:.1f} / 10"
        )
    else:
        rating_text = (
            "No rating"
        )

    header = dbc.Row(
        [
            dbc.Col(
                dbc.CardImg(
                    src=poster,
                    className=(
                        "details-poster"
                    ),
                ),
                md=3,
            ),

            dbc.Col(
                [
                    html.H5(
                        str(year)
                    ),

                    html.P(
                        rating_text,
                        className=(
                            "text-warning"
                        ),
                    ),

                    html.P(
                        overview
                        or (
                            "No description "
                            "available."
                        )
                    ),

                    html.P(
                        (
                            f"{len(episodes)} "
                            f"episodes in library"
                        ),
                        className=(
                            "text-muted"
                        ),
                    ),
                ],
                md=9,
            ),
        ],
        className="g-4 mb-4",
    )

    body = html.Div(
        [
            header,

            html.Hr(),

            *build_season_sections(
                episodes
            ),
        ]
    )

    return (
        True,
        show["title"],
        body,
        show_id,
    )


# --------------------------------------------------
# PLAY TV EPISODE
# --------------------------------------------------

@app.callback(
    Output(
        "episode-playback-message",
        "children",
    ),

    Input(
        {
            "type":
                "episode-play-button",
            "index": ALL,
        },
        "n_clicks",
    ),

    prevent_initial_call=True,
)
def play_selected_episode(
    clicks
):

    if not ctx.triggered_id:
        raise PreventUpdate

    triggered_value = (
        ctx.triggered[0]["value"]
    )

    if not triggered_value:
        raise PreventUpdate

    media_id = (
        ctx.triggered_id["index"]
    )

    media = get_media_by_id(
        media_id
    )

    if not media:

        return dbc.Alert(
            (
                "Episode file could "
                "not be found."
            ),
            color="danger",
        )

    result = play_media(
        media["path"]
    )

    if not result["success"]:

        return dbc.Alert(
            result["message"],
            color="danger",
        )

    record_play(
        media_id
    )

    return dbc.Alert(
        "Playback started.",
        color="success",
        duration=3000,
    )


# --------------------------------------------------
# RUN APP
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        debug=True
    )