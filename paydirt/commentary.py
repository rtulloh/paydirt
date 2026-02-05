"""
Colorful commentary system for Paydirt football simulation.
Generates play-by-play descriptions with player names and exciting language.
"""
import json
import os
import random
from dataclasses import dataclass, field
from typing import Optional

from .play_resolver import PlayType, ResultType


@dataclass
class TeamRoster:
    """Key players for a team used in commentary."""
    # Offense
    qb: list[str] = field(default_factory=list)  # Quarterbacks
    rb: list[str] = field(default_factory=list)  # Running backs
    wr: list[str] = field(default_factory=list)  # Wide receivers
    te: list[str] = field(default_factory=list)  # Tight ends
    ol: list[str] = field(default_factory=list)  # Offensive linemen (for run blocking mentions)

    # Defense
    dl: list[str] = field(default_factory=list)  # Defensive linemen
    lb: list[str] = field(default_factory=list)  # Linebackers
    db: list[str] = field(default_factory=list)  # Defensive backs

    # Special Teams
    k: list[str] = field(default_factory=list)   # Kickers
    p: list[str] = field(default_factory=list)   # Punters
    kr: list[str] = field(default_factory=list)  # Kick returners

    def random_qb(self) -> str:
        return random.choice(self.qb) if self.qb else "The quarterback"

    def random_rb(self) -> str:
        return random.choice(self.rb) if self.rb else "The running back"

    def random_wr(self) -> str:
        return random.choice(self.wr) if self.wr else "The receiver"

    def random_te(self) -> str:
        return random.choice(self.te) if self.te else "The tight end"

    def random_dl(self) -> str:
        return random.choice(self.dl) if self.dl else "The defensive lineman"

    def random_lb(self) -> str:
        return random.choice(self.lb) if self.lb else "The linebacker"

    def random_db(self) -> str:
        return random.choice(self.db) if self.db else "The defensive back"

    def random_defender(self) -> str:
        """Return a random defensive player."""
        all_defenders = self.dl + self.lb + self.db
        return random.choice(all_defenders) if all_defenders else "The defender"


# Team rosters for 1983 season - All 28 NFL teams
TEAM_ROSTERS = {
    # AFC EAST
    "1983 Miami Dolphins": TeamRoster(
        qb=["Dan Marino", "David Woodley"],
        rb=["Andra Franklin", "Tony Nathan", "Woody Bennett"],
        wr=["Mark Duper", "Mark Clayton", "Nat Moore", "Jimmy Cefalo"],
        te=["Bruce Hardy", "Joe Rose"],
        ol=["Dwight Stephenson", "Bob Kuechenberg", "Ed Newman", "Jon Giesler"],
        dl=["Doug Betters", "Bob Baumhower", "Kim Bokamper"],
        lb=["A.J. Duhe", "Bob Brudzinski", "Jay Brophy"],
        db=["Glenn Blackwood", "Lyle Blackwood", "Don McNeal", "William Judson"],
        k=["Uwe von Schamann"],
        p=["Reggie Roby"],
        kr=["Tony Nathan", "Fulton Walker"],
    ),
    "1983 New England Patriots": TeamRoster(
        qb=["Steve Grogan", "Tony Eason"],
        rb=["Tony Collins", "Mosi Tatupu", "Robert Weathers"],
        wr=["Stanley Morgan", "Stephen Starring", "Cedric Jones"],
        te=["Lin Dawson", "Derrick Ramsey"],
        ol=["John Hannah", "Brian Holloway", "Pete Brock"],
        dl=["Kenneth Sims", "Lester Williams", "Toby Williams"],
        lb=["Steve Nelson", "Andre Tippett", "Don Blackmon"],
        db=["Raymond Clayborn", "Rick Sanford", "Roland James", "Fred Marion"],
        k=["John Smith"],
        p=["Rich Camarillo"],
        kr=["Stephen Starring", "Tony Collins"],
    ),
    "1983 New York Jets": TeamRoster(
        qb=["Richard Todd", "Pat Ryan"],
        rb=["Freeman McNeil", "Bruce Harper", "Johnny Hector"],
        wr=["Wesley Walker", "Lam Jones", "Kurt Sohn"],
        te=["Mickey Shuler", "Rocky Klever"],
        ol=["Marvin Powell", "Joe Fields", "Dan Alexander"],
        dl=["Mark Gastineau", "Joe Klecko", "Marty Lyons", "Abdul Salaam"],
        lb=["Lance Mehl", "Greg Buttle", "Bob Crable"],
        db=["Ken Schroy", "Darrol Ray", "Bobby Jackson", "Jerry Holmes"],
        k=["Pat Leahy"],
        p=["Chuck Ramsey"],
        kr=["Bruce Harper", "Johnny Hector"],
    ),
    "1983 Buffalo Bills": TeamRoster(
        qb=["Joe Ferguson", "Matt Kofler"],
        rb=["Joe Cribbs", "Booker Moore", "Roosevelt Leaks"],
        wr=["Jerry Butler", "Frank Lewis", "Byron Franklin"],
        te=["Mark Brammer", "Pete Metzelaars"],
        ol=["Joe DeLamielleure", "Jim Ritcher", "Ken Jones"],
        dl=["Ben Williams", "Fred Smerlas", "Sherman White"],
        lb=["Jim Haslett", "Lucius Sanford", "Eugene Marve"],
        db=["Steve Freeman", "Charles Romes", "Mario Clark", "Jeff Nixon"],
        k=["Joe Danelo"],
        p=["Greg Cater"],
        kr=["Joe Cribbs", "Byron Franklin"],
    ),
    "1983 Baltimore Colts": TeamRoster(
        qb=["Mike Pagel", "Art Schlichter"],
        rb=["Curtis Dickey", "Randy McMillan", "George Wonsley"],
        wr=["Ray Butler", "Bernard Henry", "Matt Bouza"],
        te=["Pat Beach", "Reese McCall"],
        ol=["Chris Hinton", "Ray Donaldson", "Ben Utt"],
        dl=["Leo Wisniewski", "Donnell Thompson", "Blaise Winter"],
        lb=["Johnie Cooks", "Barry Krauss", "Cliff Odom"],
        db=["Derrick Hatchett", "Leonard Coleman", "Nesby Glasgow", "Preston Davis"],
        k=["Raul Allegre"],
        p=["Rohn Stark"],
        kr=["Curtis Dickey", "George Wonsley"],
    ),

    # AFC CENTRAL
    "1983 Pittsburgh Steelers": TeamRoster(
        qb=["Terry Bradshaw", "Cliff Stoudt", "David Woodley"],
        rb=["Franco Harris", "Frank Pollard", "Walter Abercrombie"],
        wr=["John Stallworth", "Calvin Sweeney", "Jim Smith"],
        te=["Bennie Cunningham", "Chris Kolodziejski"],
        ol=["Mike Webster", "Larry Brown", "Tunch Ilkin", "Craig Wolfley"],
        dl=["Gary Dunn", "Keith Gary", "Edmund Nelson"],
        lb=["Jack Lambert", "Jack Ham", "Robin Cole", "Mike Merriweather"],
        db=["Mel Blount", "Donnie Shell", "Ron Johnson", "Dwayne Woodruff"],
        k=["Gary Anderson"],
        p=["Craig Colquitt"],
        kr=["Walter Abercrombie", "Greg Hawthorne"],
    ),
    "1983 Cleveland Browns": TeamRoster(
        qb=["Brian Sipe", "Paul McDonald"],
        rb=["Mike Pruitt", "Boyce Green", "Charles White"],
        wr=["Dave Logan", "Ricky Feacher", "Dwight Walker"],
        te=["Ozzie Newsome", "Harry Holt"],
        ol=["Doug Dieken", "Robert Jackson", "Tom DeLeone", "Cody Risien"],
        dl=["Reggie Camp", "Marshall Harris", "Dave Puzzuoli"],
        lb=["Clay Matthews", "Tom Cousineau", "Dick Ambrose", "Chip Banks"],
        db=["Hanford Dixon", "Frank Minnifield", "Clarence Scott", "Al Gross"],
        k=["Matt Bahr"],
        p=["Steve Cox"],
        kr=["Dwight Walker", "Boyce Green"],
    ),
    "1983 Cincinnati Bengals": TeamRoster(
        qb=["Ken Anderson", "Turk Schonert"],
        rb=["Pete Johnson", "Charles Alexander", "James Brooks"],
        wr=["Cris Collinsworth", "Isaac Curtis", "Steve Kreider"],
        te=["Dan Ross", "M.L. Harris"],
        ol=["Anthony Munoz", "Max Montoya", "Dave Lapham", "Mike Wilson"],
        dl=["Eddie Edwards", "Ross Browner", "Wilson Whitley"],
        lb=["Reggie Williams", "Glenn Cameron", "Jim LeClair"],
        db=["Ken Riley", "Louis Breeden", "Bobby Kemp", "Ray Griffin"],
        k=["Jim Breech"],
        p=["Pat McInally"],
        kr=["James Brooks", "Steve Kreider"],
    ),
    "1983 Houston Oilers": TeamRoster(
        qb=["Gifford Nielsen", "Oliver Luck", "Archie Manning"],
        rb=["Earl Campbell", "Stan Edwards", "Larry Moriarty"],
        wr=["Tim Smith", "Harold Bailey", "Chris Dressel"],
        te=["Dave Casper", "Chris Dressel"],
        ol=["Mike Munchak", "Bruce Matthews", "Harvey Salem"],
        dl=["Elvin Bethea", "Jesse Baker", "Doug Smith"],
        lb=["Robert Brazile", "Gregg Bingham", "Avon Riley"],
        db=["Vernon Perry", "Steve Brown", "Willie Tullis", "Bo Eason"],
        k=["Florian Kempf"],
        p=["Cliff Parsley"],
        kr=["Carl Roaches", "Stan Edwards"],
    ),

    # AFC WEST
    "1983 Los Angeles Raiders": TeamRoster(
        qb=["Jim Plunkett", "Marc Wilson"],
        rb=["Marcus Allen", "Kenny King", "Frank Hawkins"],
        wr=["Cliff Branch", "Malcolm Barnwell", "Dokie Williams"],
        te=["Todd Christensen", "Dave Casper"],
        ol=["Henry Lawrence", "Mickey Marvin", "Dave Dalby", "Bruce Davis"],
        dl=["Howie Long", "Lyle Alzado", "Reggie Kinlaw", "Bill Pickel"],
        lb=["Rod Martin", "Matt Millen", "Ted Hendricks", "Bob Nelson"],
        db=["Lester Hayes", "Mike Haynes", "Vann McElroy", "Mike Davis"],
        k=["Chris Bahr"],
        p=["Ray Guy"],
        kr=["Marcus Allen", "Kenny King"],
    ),
    "1983 Seattle Seahawks": TeamRoster(
        qb=["Dave Krieg", "Jim Zorn"],
        rb=["Curt Warner", "David Hughes", "Dan Doornink"],
        wr=["Steve Largent", "Paul Johns", "Byron Walker"],
        te=["Charle Young", "Pete Metzelaars"],
        ol=["Steve August", "Blair Bush", "Edwin Bailey"],
        dl=["Jacob Green", "Jeff Bryant", "Manu Tuiasosopo", "Joe Nash"],
        lb=["Michael Jackson", "Keith Butler", "Shelton Robinson"],
        db=["Dave Brown", "Kenny Easley", "John Harris", "Kerry Justin"],
        k=["Norm Johnson"],
        p=["Jeff West"],
        kr=["Zachary Dixon", "Paul Johns"],
    ),
    "1983 Denver Broncos": TeamRoster(
        qb=["John Elway", "Steve DeBerg"],
        rb=["Sammy Winder", "Rick Parros", "Gerald Willhite"],
        wr=["Steve Watson", "Rick Upchurch", "Butch Johnson"],
        te=["James Wright", "Ron Egloff"],
        ol=["Keith Bishop", "Tom Glassic", "Billy Bryan", "Dave Studdard"],
        dl=["Rulon Jones", "Barney Chavous", "Rubin Carter"],
        lb=["Tom Jackson", "Randy Gradishar", "Bob Swenson", "Steve Busick"],
        db=["Louis Wright", "Dennis Smith", "Steve Foley", "Mike Harden"],
        k=["Rich Karlis"],
        p=["Luke Prestridge"],
        kr=["Rick Upchurch", "Gerald Willhite"],
    ),
    "1983 San Diego Chargers": TeamRoster(
        qb=["Dan Fouts", "Ed Luther"],
        rb=["Chuck Muncie", "James Brooks", "Earnest Jackson"],
        wr=["Charlie Joiner", "Wes Chandler", "Bobby Duckworth"],
        te=["Kellen Winslow", "Eric Sievers"],
        ol=["Russ Washington", "Doug Wilkerson", "Don Macek", "Ed White"],
        dl=["Gary Johnson", "Louie Kelcher", "Fred Dean", "Leroy Jones"],
        lb=["Woodrow Lowe", "Linden King", "Billy Ray Smith"],
        db=["Gill Byrd", "Danny Walters", "Pete Shaw", "Tim Fox"],
        k=["Rolf Benirschke"],
        p=["Maury Buford"],
        kr=["Lionel James", "Bobby Duckworth"],
    ),
    "1983 Kansas City Chiefs": TeamRoster(
        qb=["Bill Kenney", "Todd Blackledge"],
        rb=["Joe Delaney", "Theotis Brown", "Billy Jackson"],
        wr=["Carlos Carson", "Henry Marshall", "Stephone Paige"],
        te=["Willie Scott", "Walter White"],
        ol=["John Alt", "Tom Condon", "Bob Rush", "Matt Herkenhoff"],
        dl=["Art Still", "Mike Bell", "Bill Maas"],
        lb=["Gary Spani", "Thomas Howard", "Calvin Daniels"],
        db=["Gary Barbaro", "Gary Green", "Deron Cherry", "Albert Lewis"],
        k=["Nick Lowery"],
        p=["Jim Arnold"],
        kr=["Theotis Brown", "Stephone Paige"],
    ),

    # NFC EAST
    "1983 Washington Redskins": TeamRoster(
        qb=["Joe Theismann", "Joe Washington"],
        rb=["John Riggins", "Joe Washington", "Clarence Harmon"],
        wr=["Art Monk", "Charlie Brown", "Virgil Seay", "Alvin Garrett"],
        te=["Don Warren", "Rick Walker", "Clint Didier"],
        ol=["Joe Jacoby", "Russ Grimm", "Jeff Bostic", "Mark May", "George Starke"],
        dl=["Dexter Manley", "Dave Butz", "Darryl Grant", "Charles Mann"],
        lb=["Rich Milot", "Neal Olkewicz", "Monte Coleman"],
        db=["Darrell Green", "Vernon Dean", "Mark Murphy", "Tony Peters"],
        k=["Mark Moseley"],
        p=["Jeff Hayes"],
        kr=["Mike Nelms", "Darrell Green"],
    ),
    "1983 Dallas Cowboys": TeamRoster(
        qb=["Danny White", "Gary Hogeboom"],
        rb=["Tony Dorsett", "Ron Springs", "Timmy Newsome"],
        wr=["Tony Hill", "Drew Pearson", "Butch Johnson", "Doug Donley"],
        te=["Doug Cosbie", "Billy Joe DuPree"],
        ol=["Pat Donovan", "Herbert Scott", "Tom Rafferty", "Kurt Petersen"],
        dl=["Ed Jones", "Randy White", "Harvey Martin", "John Dutton"],
        lb=["Bob Breunig", "Mike Hegman", "Anthony Dickerson"],
        db=["Everson Walls", "Dennis Thurman", "Michael Downs", "Dexter Clinkscale"],
        k=["Rafael Septien"],
        p=["Danny White"],
        kr=["Ron Springs", "James Jones"],
    ),
    "1983 St. Louis Cardinals": TeamRoster(
        qb=["Neil Lomax", "Jim Hart"],
        rb=["Ottis Anderson", "Stump Mitchell", "Earl Ferrell"],
        wr=["Roy Green", "Pat Tilley", "Doug Marsh"],
        te=["Doug Marsh", "Jay Novacek"],
        ol=["Luis Sharpe", "Terry Stieve", "Randy Clark", "Joe Bostic"],
        dl=["Curtis Greer", "Mark Duda", "David Galloway"],
        lb=["E.J. Junior", "Thomas Howard", "Charlie Baker"],
        db=["Roger Wehrli", "Leonard Smith", "Lionel Washington", "Jeff Griffin"],
        k=["Neil O'Donoghue"],
        p=["Carl Birdsong"],
        kr=["Stump Mitchell", "Roy Green"],
    ),
    "1983 Philadelphia Eagles": TeamRoster(
        qb=["Ron Jaworski", "Joe Pisarcik"],
        rb=["Wilbert Montgomery", "Hubert Oliver", "Michael Williams"],
        wr=["Mike Quick", "Harold Carmichael", "Ron Smith"],
        te=["John Spagnola", "Vyto Kab"],
        ol=["Jerry Sisemore", "Steve Kenney", "Guy Morriss", "Dean Miraldi"],
        dl=["Dennis Harrison", "Charlie Johnson", "Carl Hairston", "Greg Brown"],
        lb=["Jerry Robinson", "Frank LeMaster", "Reggie Wilkes"],
        db=["Herman Edwards", "Roynell Young", "Wes Hopkins", "Ray Ellis"],
        k=["Tony Franklin"],
        p=["Max Runager"],
        kr=["Wilbert Montgomery", "Ron Smith"],
    ),
    "1983 New York Giants": TeamRoster(
        qb=["Phil Simms", "Scott Brunner"],
        rb=["Butch Woolfolk", "Rob Carpenter", "Joe Morris"],
        wr=["Earnest Gray", "Johnny Perkins", "Byron Williams"],
        te=["Zeke Mowatt", "Tom Mullady"],
        ol=["Brad Benson", "Bill Ard", "Bart Oates", "Karl Nelson"],
        dl=["Leonard Marshall", "George Martin", "Curtis McGriff", "Jim Burt"],
        lb=["Lawrence Taylor", "Harry Carson", "Brian Kelley", "Byron Hunt"],
        db=["Mark Haynes", "Terry Jackson", "Bill Currier", "Beasley Reece"],
        k=["Ali Haji-Sheikh"],
        p=["Dave Jennings"],
        kr=["Leon Bright", "Butch Woolfolk"],
    ),

    # NFC CENTRAL
    "1983 Chicago Bears": TeamRoster(
        qb=["Jim McMahon", "Vince Evans"],
        rb=["Walter Payton", "Matt Suhey", "Calvin Thomas"],
        wr=["Willie Gault", "Dennis McKinnon", "Ken Margerum"],
        te=["Emery Moorehead", "Pat Dunsmore"],
        ol=["Jim Covert", "Mark Bortz", "Jay Hilgenberg", "Keith Van Horne"],
        dl=["Dan Hampton", "Steve McMichael", "Richard Dent", "Mike Hartenstine"],
        lb=["Mike Singletary", "Otis Wilson", "Wilber Marshall"],
        db=["Gary Fencik", "Dave Duerson", "Leslie Frazier", "Mike Richardson"],
        k=["Bob Thomas"],
        p=["Dave Finzer"],
        kr=["Willie Gault", "Dennis McKinnon"],
    ),
    "1983 Detroit Lions": TeamRoster(
        qb=["Gary Danielson", "Eric Hipple"],
        rb=["Billy Sims", "Dexter Bussey", "James Jones"],
        wr=["Leonard Thompson", "Mark Nichols", "Jeff Chadwick"],
        te=["David Hill", "Ulysses Norris"],
        ol=["Keith Dorney", "Russ Bolinger", "Steve Mott", "Harvey Salem"],
        dl=["Doug English", "William Gay", "Dave Pureifory"],
        lb=["Ken Fantetti", "Garry Cobb", "Jimmy Williams"],
        db=["Bruce McNorton", "Bobby Watkins", "William Graham", "Demetrious Johnson"],
        k=["Eddie Murray"],
        p=["Mike Black"],
        kr=["Robbie Martin", "James Jones"],
    ),
    "1983 Green Bay Packers": TeamRoster(
        qb=["Lynn Dickey", "David Whitehurst"],
        rb=["Gerry Ellis", "Eddie Lee Ivery", "Jessie Clark"],
        wr=["James Lofton", "John Jefferson", "Phillip Epps"],
        te=["Paul Coffman", "Gary Lewis"],
        ol=["Greg Koch", "Karl Swanke", "Larry McCarren", "Syd Kitson"],
        dl=["Ezra Johnson", "Mike Butler", "Terry Jones"],
        lb=["Mike Douglass", "John Anderson", "Randy Scott"],
        db=["Tim Lewis", "Mark Lee", "Mark Murphy", "Maurice Harvey"],
        k=["Jan Stenerud"],
        p=["Ray Stachowicz"],
        kr=["Phillip Epps", "Eddie Lee Ivery"],
    ),
    "1983 Minnesota Vikings": TeamRoster(
        qb=["Tommy Kramer", "Steve Dils", "Wade Wilson"],
        rb=["Ted Brown", "Darrin Nelson", "Tony Galbreath"],
        wr=["Sammy White", "Anthony Carter", "Leo Lewis"],
        te=["Steve Jordan", "Bob Bruer"],
        ol=["Ron Yary", "Dennis Swilley", "Tim Irwin", "Steve Riley"],
        dl=["Doug Martin", "Charlie Johnson", "Mark Mullaney", "Neil Elshire"],
        lb=["Matt Blair", "Scott Studwell", "Fred McNeill", "Dennis Johnson"],
        db=["Joey Browner", "John Turner", "Willie Teal", "Rufus Bess"],
        k=["Benny Ricardo"],
        p=["Greg Coleman"],
        kr=["Darrin Nelson", "Leo Lewis"],
    ),
    "1983 Tampa Bay Buccaneers": TeamRoster(
        qb=["Doug Williams", "Jerry Golsteyn", "Jack Thompson"],
        rb=["James Wilder", "Jerry Eckwood", "Adger Armstrong"],
        wr=["Kevin House", "Theo Bell", "Gerald Carter"],
        te=["Jimmie Giles", "Jerry Bell"],
        ol=["Dave Reavis", "Sean Farrell", "Steve Wilson", "Gene Sanders"],
        dl=["Lee Roy Selmon", "David Logan", "John Cannon"],
        lb=["Hugh Green", "Richard Wood", "Scot Brantley", "Jeff Davis"],
        db=["Cedric Brown", "Neal Colzie", "Mark Cotney", "Jeremiah Castille"],
        k=["Bill Capece"],
        p=["Frank Garcia"],
        kr=["Adger Armstrong", "Leon Bright"],
    ),

    # NFC WEST
    "1983 San Francisco 49ers": TeamRoster(
        qb=["Joe Montana", "Matt Cavanaugh"],
        rb=["Wendell Tyler", "Roger Craig", "Bill Ring"],
        wr=["Dwight Clark", "Freddie Solomon", "Renaldo Nehemiah"],
        te=["Russ Francis", "Earl Cooper"],
        ol=["Keith Fahnhorst", "Randy Cross", "Fred Quillan", "John Ayers"],
        dl=["Fred Dean", "Dwaine Board", "Gary Johnson", "Manu Tuiasosopo"],
        lb=["Keena Turner", "Jack Reynolds", "Riki Ellison", "Dan Bunz"],
        db=["Ronnie Lott", "Eric Wright", "Carlton Williamson", "Dwight Hicks"],
        k=["Ray Wersching"],
        p=["Tom Orosz"],
        kr=["Dana McLemore", "Bill Ring"],
    ),
    "1983 Los Angeles Rams": TeamRoster(
        qb=["Vince Ferragamo", "Jeff Kemp"],
        rb=["Eric Dickerson", "Barry Redden", "Dwayne Crutchfield"],
        wr=["Henry Ellard", "Drew Hill", "George Farmer"],
        te=["David Hill", "Mike Barber"],
        ol=["Jackie Slater", "Kent Hill", "Doug Smith", "Dennis Harrah"],
        dl=["Jack Youngblood", "Gary Jeter", "Reggie Doss", "Mike Fanning"],
        lb=["Jim Collins", "Carl Ekern", "Mel Owens", "George Andrews"],
        db=["Nolan Cromwell", "Johnnie Johnson", "LeRoy Irvin", "Gary Green"],
        k=["Mike Lansford"],
        p=["Dale Hatcher"],
        kr=["Henry Ellard", "LeRoy Irvin"],
    ),
    "1983 New Orleans Saints": TeamRoster(
        qb=["Ken Stabler", "Richard Todd", "Dave Wilson"],
        rb=["George Rogers", "Wayne Wilson", "Hokie Gajan"],
        wr=["Wes Chandler", "Eugene Goodlow", "Lindsay Scott"],
        te=["Hoby Brenner", "John Tice"],
        ol=["Stan Brock", "Brad Edelman", "Joel Hilgenberg", "Kelvin Clark"],
        dl=["Bruce Clark", "Derland Moore", "Frank Warren"],
        lb=["Rickey Jackson", "Jim Kovach", "Whitney Paul", "Dennis Winston"],
        db=["Dave Waymer", "Johnnie Poe", "Russell Gary", "Frank Wattelet"],
        k=["Morten Andersen"],
        p=["Russell Erxleben"],
        kr=["Tyrone Young", "Wayne Wilson"],
    ),
    "1983 Atlanta Falcons": TeamRoster(
        qb=["Steve Bartkowski", "Mike Moroski"],
        rb=["William Andrews", "Gerald Riggs", "Lynn Cain"],
        wr=["Alfred Jenkins", "Billy Johnson", "Stacey Bailey"],
        te=["Arthur Cox", "Floyd Hodge"],
        ol=["Mike Kenn", "R.C. Thielemann", "Jeff Van Note", "Bill Fralic"],
        dl=["Mike Pitts", "Jeff Merrow", "Don Smith"],
        lb=["Buddy Curry", "Joel Williams", "Al Richardson", "John Rade"],
        db=["Bobby Butler", "Scott Case", "Kenny Johnson", "Tom Pridemore"],
        k=["Mick Luckhurst"],
        p=["Ralph Giacomarro"],
        kr=["Billy Johnson", "Gerald Riggs"],
    ),
}


def load_roster_from_file(team_dir: str) -> Optional[TeamRoster]:
    """Load roster from a JSON file in the team directory."""
    roster_path = os.path.join(team_dir, "roster.json")
    if os.path.exists(roster_path):
        try:
            with open(roster_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return TeamRoster(
                qb=data.get("qb", []),
                rb=data.get("rb", []),
                wr=data.get("wr", []),
                te=data.get("te", []),
                ol=data.get("ol", []),
                dl=data.get("dl", []),
                lb=data.get("lb", []),
                db=data.get("db", []),
                k=data.get("k", []),
                p=data.get("p", []),
                kr=data.get("kr", []),
            )
        except (json.JSONDecodeError, IOError):
            pass
    return None


# Cache for loaded rosters
_roster_cache: dict[str, TeamRoster] = {}


def get_roster(team_full_name: str, team_dir: str = None) -> TeamRoster:
    """
    Get roster for a team. First tries to load from team directory JSON file,
    then falls back to hardcoded TEAM_ROSTERS dictionary.
    
    Args:
        team_full_name: Full team name like "1983 Chicago Bears"
        team_dir: Optional path to team directory containing roster.json
    
    Returns:
        TeamRoster with player names, or empty roster if not found
    """
    # Check cache first
    cache_key = team_dir or team_full_name
    if cache_key in _roster_cache:
        return _roster_cache[cache_key]

    # Try loading from file if team_dir provided
    if team_dir:
        roster = load_roster_from_file(team_dir)
        if roster:
            _roster_cache[cache_key] = roster
            return roster

    # Fall back to hardcoded rosters
    roster = TEAM_ROSTERS.get(team_full_name, TeamRoster())
    _roster_cache[cache_key] = roster
    return roster


# Commentary templates
TOUCHDOWN_CALLS = [
    "TOUCHDOWN! {team}! What a play!",
    "HE'S IN! TOUCHDOWN {team}!",
    "SCORE! {team} finds the end zone!",
    "AND IT'S A TOUCHDOWN! {team} strikes!",
    "SIX POINTS! {team} punches it in!",
    "THEY SCORE! Incredible play by {team}!",
    "TOUCHDOWN! The crowd goes wild!",
    "INTO THE END ZONE! TOUCHDOWN {team}!",
]

RUSHING_TD_CALLS = [
    "{player} powers into the end zone! TOUCHDOWN {team}!",
    "{player} breaks through! TOUCHDOWN!",
    "{player} will NOT be denied! TOUCHDOWN {team}!",
    "{player} punches it in from {yards} yards out! TOUCHDOWN!",
    "A magnificent run by {player}! TOUCHDOWN {team}!",
]

PASSING_TD_CALLS = [
    "{qb} finds {receiver} in the end zone! TOUCHDOWN {team}!",
    "{qb} to {receiver}... TOUCHDOWN!",
    "What a throw by {qb}! {receiver} hauls it in for the score!",
    "{qb} launches it... {receiver} makes the catch! TOUCHDOWN {team}!",
    "A perfect strike from {qb} to {receiver}! TOUCHDOWN!",
]

BIG_RUN_CALLS = [
    "{player} breaks free! {yards} yards!",
    "{player} finds a hole and he's GONE! {yards} yards!",
    "Look at {player} go! A gain of {yards}!",
    "{player} sheds a tackle and picks up {yards} yards!",
    "Great blocking! {player} rumbles for {yards}!",
    "{player} with a burst through the line for {yards} yards!",
]

BIG_PASS_CALLS = [
    "{qb} connects with {receiver} for {yards} yards!",
    "{qb} finds {receiver} wide open! {yards} yard gain!",
    "What a catch by {receiver}! {yards} yards on the play!",
    "{qb} drops back... fires... {receiver} has it for {yards}!",
    "A beautiful throw from {qb} to {receiver}! {yards} yards!",
    "{receiver} makes a spectacular grab! {yards} yard pickup!",
]

SHORT_RUN_GAIN_CALLS = [
    "{player} picks up {yards}.",
    "A gain of {yards} on the play.",
    "{player} grinds out {yards} yards.",
    "{player} fights for {yards}.",
    "Tough running by {player} for {yards}.",
]

SHORT_PASS_GAIN_CALLS = [
    "{receiver} catches it for {yards}.",
    "A gain of {yards} on the reception.",
    "{receiver} makes the catch for {yards} yards.",
    "{receiver} holds on for {yards}.",
    "Nice grab by {receiver} for {yards}.",
]

# Check-down calls when defense limits the gain (parentheses result)
CHECK_DOWN_CALLS = [
    "{qb} had to check down to {checkdown_receiver} - {primary_receiver} was covered. {yards} yards.",
    "Good coverage forces {qb} to dump it off to {checkdown_receiver} for {yards}.",
    "{primary_receiver} blanketed! {qb} finds {checkdown_receiver} underneath for {yards}.",
    "Tight coverage! {qb} checks down to {checkdown_receiver} for a short gain of {yards}.",
    "{qb} looks deep but settles for {checkdown_receiver} for {yards}.",
    "The defense takes away the deep ball. {qb} dumps it to {checkdown_receiver} for {yards}.",
]

NO_GAIN_CALLS = [
    "{player} is stopped at the line.",
    "No gain on the play.",
    "The defense holds! No gain.",
    "{player} goes nowhere.",
    "Stuffed at the line of scrimmage!",
]

LOSS_CALLS = [
    "{player} is dropped for a loss of {yards}!",
    "Loss of {yards} on the play!",
    "{player} is hit in the backfield! Loss of {yards}!",
    "The defense blows this one up! {yards} yard loss!",
]

SACK_CALLS = [
    "SACK! {defender} brings down {qb}!",
    "{defender} gets to {qb}! SACKED for a loss of {yards}!",
    "{qb} is BURIED by {defender}!",
    "HUGE SACK! {defender} was unblocked!",
    "{defender} crashes through and sacks {qb}!",
    "DOWN GOES {qb}! {defender} with the sack!",
    "The pocket collapses! {qb} is sacked by {defender}!",
]

QB_SCRAMBLE_CALLS = [
    "{qb} scrambles out of trouble! {yards} yards!",
    "{qb} escapes the rush and picks up {yards}!",
    "Pressure! {qb} takes off and gains {yards}!",
    "{qb} buys time and scrambles for {yards}!",
    "Nobody open! {qb} tucks it and runs for {yards}!",
    "{qb} avoids the sack and scrambles for {yards}!",
    "Great escape by {qb}! Picks up {yards} on the ground!",
    "{qb} uses his legs! {yards} yard scramble!",
]

QB_SCRAMBLE_TD_CALLS = [
    "{qb} scrambles... TOUCHDOWN!",
    "{qb} escapes and takes it to the house! TOUCHDOWN!",
    "Nobody can catch {qb}! Scrambles for the TOUCHDOWN!",
    "{qb} with the legs! TOUCHDOWN on the scramble!",
]

QB_SCRAMBLE_LOSS_CALLS = [
    "{qb} scrambles but loses {yards}!",
    "{qb} tries to escape but is brought down for a loss of {yards}!",
    "Nowhere to go! {qb} scrambles but loses {yards}!",
]

INTERCEPTION_CALLS = [
    "INTERCEPTED! {defender} picks it off!",
    "PICKED OFF! {defender} jumps the route!",
    "{qb}'s pass is INTERCEPTED by {defender}!",
    "TURNOVER! {defender} with the interception!",
    "What a play by {defender}! INTERCEPTION!",
    "{defender} reads it all the way! PICKED OFF!",
    "BAD DECISION! {defender} comes away with the INT!",
]

FUMBLE_CALLS = [
    "FUMBLE! {team} recovers!",
    "HE LOST IT! {team} falls on the loose ball!",
    "The ball is out! {team} recovers the fumble!",
    "TURNOVER! Fumble recovered by {team}!",
    "A costly fumble! {team} takes over!",
]

INCOMPLETE_CALLS = [
    "Pass incomplete.",
    "The pass falls incomplete.",
    "Intended for {receiver}... incomplete.",
    "{qb}'s pass is batted away. Incomplete.",
    "No one there. Incomplete pass.",
    "The throw is off target. Incomplete.",
    "Dropped! The pass hits the ground.",
]

FIRST_DOWN_CALLS = [
    "First down {team}!",
    "That's a {team} first down!",
    "Moving the chains! First down!",
    "First down and more!",
    "{team} moves the chains!",
    "That's enough for a first down!",
]

PENALTY_OFFENSE_CALLS = [
    "FLAG DOWN! Penalty on the offense.",
    "Yellow flag! Offensive penalty.",
    "Penalty against the offense. {yards} yards.",
    "That'll cost them! {yards} yard penalty on the offense.",
]

PENALTY_DEFENSE_CALLS = [
    "FLAG! Penalty on the defense!",
    "The defense is flagged! {yards} yards!",
    "Defensive penalty! {yards} yards!",
    "Gift from the defense! {yards} yard penalty!",
]

PASS_INTERFERENCE_CALLS = [
    "FLAG! Pass interference on the defense!",
    "PI! The defender grabbed him! Automatic first down!",
    "Pass interference! Big penalty on the defense!",
    "He was all over the receiver! Pass interference!",
]

BREAKAWAY_CALLS = [
    "{player} breaks loose! HE COULD GO ALL THE WAY!",
    "LOOK OUT! {player} has daylight!",
    "{player} is GONE! Nobody's going to catch him!",
    "A HUGE hole! {player} takes off!",
    "{player} makes a man miss and he's got room to run!",
]


class Commentary:
    """Generates colorful play-by-play commentary."""

    def __init__(self, offense_roster: TeamRoster, defense_roster: TeamRoster,
                 offense_name: str, defense_name: str):
        self.off_roster = offense_roster
        self.def_roster = defense_roster
        self.off_name = offense_name
        self.def_name = defense_name

    def generate(self, play_type: PlayType, result_type: ResultType,
                 yards: int, is_first_down: bool = False,
                 is_touchdown: bool = False, is_breakaway: bool = False,
                 is_check_down: bool = False) -> str:
        """Generate commentary for a play result.
        
        Args:
            play_type: The type of play called
            result_type: The result type (yards, TD, INT, etc.)
            yards: Yards gained/lost
            is_first_down: Whether the play resulted in a first down
            is_touchdown: Whether the play resulted in a touchdown
            is_breakaway: Whether this was a breakaway run
            is_check_down: Whether defense limited the gain (parentheses result)
        """
        lines = []

        # Determine if this is a pass or run play
        is_pass = play_type in [
            PlayType.SHORT_PASS, PlayType.MEDIUM_PASS,
            PlayType.LONG_PASS, PlayType.SCREEN, PlayType.TE_SHORT_LONG
        ]

        # Get player names
        # Use starting QB (first in list) for passing plays to avoid backup QBs
        # who might also be listed as RBs (e.g., Joe Washington)
        qb = self.off_roster.qb[0] if self.off_roster.qb else "The quarterback"
        rb = self.off_roster.random_rb()
        wr = self.off_roster.random_wr()
        te = self.off_roster.random_te()
        self.def_roster.random_defender()
        db = self.def_roster.random_db()
        dl = self.def_roster.random_dl()
        lb = self.def_roster.random_lb()

        # Choose receiver based on play type
        if play_type == PlayType.TE_SHORT_LONG:
            receiver = te
        elif play_type == PlayType.SCREEN:
            # Screen pass goes to RB, but make sure it's not the same as QB
            receiver = rb
            if receiver == qb and len(self.off_roster.rb) > 1:
                # Pick a different RB
                for other_rb in self.off_roster.rb:
                    if other_rb != qb:
                        receiver = other_rb
                        break
        else:
            receiver = wr

        # Choose ball carrier for runs
        # QB Sneak means the QB runs the ball
        if play_type == PlayType.QB_SNEAK:
            ball_carrier = qb
        else:
            ball_carrier = rb

        # Generate commentary based on result type
        if result_type == ResultType.TOUCHDOWN:
            if is_pass:
                template = random.choice(PASSING_TD_CALLS)
                lines.append(template.format(
                    qb=qb, receiver=receiver, team=self.off_name, yards=yards
                ))
            else:
                template = random.choice(RUSHING_TD_CALLS)
                lines.append(template.format(
                    player=ball_carrier, team=self.off_name, yards=yards
                ))

        elif result_type == ResultType.INTERCEPTION:
            template = random.choice(INTERCEPTION_CALLS)
            lines.append(template.format(
                qb=qb, defender=db, team=self.def_name
            ))

        elif result_type == ResultType.FUMBLE:
            template = random.choice(FUMBLE_CALLS)
            lines.append(template.format(team=self.def_name))

        elif result_type == ResultType.SACK:
            template = random.choice(SACK_CALLS)
            lines.append(template.format(
                qb=qb, defender=random.choice([dl, lb]), yards=abs(yards)
            ))

        elif result_type == ResultType.QB_SCRAMBLE:
            # QB scramble - escaped pressure and ran
            if is_touchdown:
                template = random.choice(QB_SCRAMBLE_TD_CALLS)
                lines.append(template.format(qb=qb))
            elif yards < 0:
                template = random.choice(QB_SCRAMBLE_LOSS_CALLS)
                lines.append(template.format(qb=qb, yards=abs(yards)))
            else:
                template = random.choice(QB_SCRAMBLE_CALLS)
                lines.append(template.format(qb=qb, yards=yards))

        elif result_type == ResultType.INCOMPLETE:
            template = random.choice(INCOMPLETE_CALLS)
            lines.append(template.format(qb=qb, receiver=receiver))

        elif result_type == ResultType.PENALTY_OFFENSE:
            template = random.choice(PENALTY_OFFENSE_CALLS)
            lines.append(template.format(yards=abs(yards)))

        elif result_type == ResultType.PENALTY_DEFENSE:
            template = random.choice(PENALTY_DEFENSE_CALLS)
            lines.append(template.format(yards=yards))

        elif result_type == ResultType.PASS_INTERFERENCE:
            template = random.choice(PASS_INTERFERENCE_CALLS)
            lines.append(template.format(yards=yards))

        elif result_type == ResultType.BREAKAWAY:
            # Breakaway run
            template = random.choice(BREAKAWAY_CALLS)
            lines.append(template.format(player=ball_carrier, yards=yards))
            if is_touchdown:
                lines.append(random.choice(TOUCHDOWN_CALLS).format(team=self.off_name))

        elif result_type == ResultType.YARDS:
            # Normal yardage play
            if is_touchdown:
                if is_pass:
                    template = random.choice(PASSING_TD_CALLS)
                    lines.append(template.format(
                        qb=qb, receiver=receiver, team=self.off_name, yards=yards
                    ))
                else:
                    template = random.choice(RUSHING_TD_CALLS)
                    lines.append(template.format(
                        player=ball_carrier, team=self.off_name, yards=yards
                    ))
            elif yards >= 15:
                # Big play
                if is_pass:
                    template = random.choice(BIG_PASS_CALLS)
                    lines.append(template.format(
                        qb=qb, receiver=receiver, yards=yards
                    ))
                else:
                    template = random.choice(BIG_RUN_CALLS)
                    lines.append(template.format(player=ball_carrier, yards=yards))
            elif yards > 0:
                # Normal gain
                if is_pass:
                    # Check-down commentary when defense limited the gain
                    if is_check_down and play_type in [PlayType.MEDIUM_PASS, PlayType.LONG_PASS]:
                        # Primary receiver was covered, had to check down to RB or TE
                        checkdown_receiver = random.choice([rb, te])
                        template = random.choice(CHECK_DOWN_CALLS)
                        lines.append(template.format(
                            qb=qb, checkdown_receiver=checkdown_receiver,
                            primary_receiver=wr, yards=yards
                        ))
                    else:
                        template = random.choice(SHORT_PASS_GAIN_CALLS)
                        lines.append(template.format(
                            receiver=receiver, yards=yards
                        ))
                else:
                    template = random.choice(SHORT_RUN_GAIN_CALLS)
                    lines.append(template.format(player=ball_carrier, yards=yards))
            elif yards == 0:
                template = random.choice(NO_GAIN_CALLS)
                lines.append(template.format(player=ball_carrier if not is_pass else receiver))
            else:
                # Loss
                template = random.choice(LOSS_CALLS)
                lines.append(template.format(
                    player=ball_carrier if not is_pass else qb, yards=abs(yards)
                ))

        # Add first down call if applicable (and not a touchdown)
        if is_first_down and not is_touchdown:
            lines.append(random.choice(FIRST_DOWN_CALLS).format(team=self.off_name))

        return " ".join(lines)
