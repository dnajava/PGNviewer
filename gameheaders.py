class GameHeaders:
    """PGN-tiedoston header-osio (kaikki standardit tagit)"""
    event:      str = "?"
    site:       str = "?"
    date:       Optional[date] = None
    round:      str = "?"
    white:      Player = field(default_factory=Player)
    black:      Player = Player(name="?")
    result:     Result = Result.ONGOING
    eco:        Optional[str] = None
    opening:    Optional[str] = None
    variation:  Optional[str] = None

    # Lisää tarvittaessa: annotator, plycount terminaton jne.