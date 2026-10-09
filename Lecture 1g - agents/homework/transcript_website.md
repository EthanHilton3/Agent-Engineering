
---

# Transcript 2026-10-09 09:47 (model=gpt-5.6-sol, reasoning=medium, auto=False, search_context_size=medium)

**USER:** ok agent, today i want to build a website. I want the site to be the ultimate personal media tracker app, where a user comes after cosuming any type of media (watchig an epsidoe of a tv show, watching a movie, reading a chapter in a book, listngin to an audiobook, going to a concert/play/musical) with all the desired information (what they watched/read, where they were when they did it, with whom they were, if they finsihed it or just started it, if its a book or movie what specific coy of it did you use, etc). CAn you think of other information we should track? I wasnt to track everything but not make it to much fo the user. And then with all the datat we'll be able to have a media page that has a section to view everything you've comn=sume of a certain type of media (a sectino for movies, for books, for video games). And then another section called time line that will show a super cool ui disaply of eveyrthing you've consumed in a visually recognizable and effecient way. Cna you ehlp me draft a pgroject spec for this including the tech stack, the database scehema, and the website interface and design? Let's just start with the idea, what are you most immediate impressions and suggestions of the idea and how to polish it.

**AGENT:** # Immediate impression

This is a **strong idea with a clear emotional value**: it’s not merely a list of books, movies, and games—it becomes a personal history told through media.

Most existing trackers focus on one medium or only record completion. Your differentiator could be:

> **Track not only what you consumed, but when, where, how, and with whom you experienced it.**

That makes the timeline much more meaningful than a standard watchlist or reading log.

## The main product challenge

“Track everything” and “don’t overwhelm the user” naturally conflict.

The solution should be **progressive detail**:

1. Logging something should take **5–15 seconds**.
2. Optional details can be added afterward.
3. The app should remember common answers.
4. Most metadata should be imported or inferred automatically.

For example, the default movie check-in might ask only:

- What did you watch?
- Did you finish it?
- When?

Then an expandable **Add details** section could contain:

- Where?
- With whom?
- Which version or format?
- How did you watch it?
- Rating, reaction, notes, photos, and tags.

---

# The core concept: experiences, not just titles

I recommend designing the product around a **consumption event** or **media experience**.

A user does not simply mark *The Lord of the Rings* as watched. They record:

> Watched *The Fellowship of the Ring* on October 8, 2026, at home, on Blu-ray, with Alex, and finished it.

That distinction will make the database and interface much more powerful.

The product would have four fundamental concepts:

### 1. Media item

The underlying work:

- Movie
- TV show
- Book
- Audiobook
- Podcast
- Album or song
- Video game
- Concert
- Play or musical
- Comic or manga
- YouTube video or web series

### 2. Edition, release, or copy

The particular version consumed:

- Hardcover versus paperback
- First edition versus later edition
- The user’s personally owned copy
- Theatrical versus director’s cut
- Blu-ray versus streaming release
- Remaster or deluxe album edition
- Original versus translated edition
- Console/platform and game edition
- Audiobook narrator and production

### 3. Consumption session

An individual interaction:

- Watched one episode
- Read three chapters
- Played a game for 90 minutes
- Listened to 40 minutes of an audiobook
- Attended a concert
- Rewatched part of a movie

### 4. Overall progress

The user’s relationship with the media:

- Want to consume
- In progress
- Completed
- Paused
- Abandoned
- Rewatching/rereading/replaying
- Consumed multiple times

Separating sessions from overall progress is critical. It allows the app to understand that someone read a book over twelve sessions rather than treating it as a single completed entry.

---

# Information worth tracking

## Universal information

These fields can apply to nearly every media type:

- Date and time
- Start and end time
- Progress before and after the session
- Status: started, continued, completed, paused, abandoned
- Location
- Companions
- Format or platform
- Personal rating
- Short reaction or mood
- Private notes
- Tags
- Photos or attachments
- First-time consumption or repeat
- How the user discovered it
- Who recommended it
- Whether the entry is private or shareable

## Contextual information

These details could make the app special:

- **Why did you choose it?**
  - Recommendation
  - Book club
  - Required reading
  - Random choice
  - Part of a series
  - Related to a current event
- **How did it make you feel?**
  - A small set of mood/reaction chips
- **Attention level**
  - Fully engaged
  - Casual/background
  - Fell asleep
- **Social context**
  - Alone
  - With friends
  - With family
  - Date
  - Audience/event
- **Environment**
  - Home
  - Theater
  - Transit
  - Vacation
  - School/work
  - Venue
- **Ownership**
  - Owned
  - Borrowed
  - Rented
  - Library
  - Subscription
  - Gifted

These should remain optional. They become valuable over time but should never block a quick entry.

## Media-specific fields

### Movies and TV

- Theater, streaming service, disc, broadcast, or file
- Cut/version
- Episode and season
- Subtitles or dubbed language
- Theater and screen
- Rewatch count
- Started versus finished

### Books, comics, and manga

- Page or chapter range
- Edition and ISBN
- Physical, ebook, or audiobook
- Language or translation
- Owned, borrowed, or library copy
- Copy-specific notes or annotations
- Reading time

### Audiobooks and podcasts

- Timestamp range
- Playback speed
- Narrator or host
- Listening platform
- Episode number
- Whether listening was active or in the background

### Video games

- Platform
- Playtime for the session
- Save file or playthrough
- Story progress
- Difficulty
- Solo or multiplayer
- People played with
- Achievements or milestones
- Main story completed versus 100% completion

### Live performances

- Venue
- City
- Seat or section
- Performers or cast
- Tour or production
- Opening acts
- Setlist
- Ticket information
- Photos
- Who attended with the user

---

# How to prevent excessive effort

## 1. Use progressive disclosure

Show only the most relevant fields first. Hide the rest behind **Add details**.

## 2. Customize the form by medium

A movie form should not ask for page numbers, and a book form should not ask for theater seating.

## 3. Learn the user’s habits

The app can suggest:

- “At home” as the usual location
- A frequently used streaming service
- Common companions
- The user’s current book edition
- The last known progress point

## 4. Automatically import metadata

Users should search for a title and have the app populate:

- Cover or poster
- Creator
- Release date
- Genre
- Runtime or page count
- Series relationships
- Cast or contributors

Users should not manually type information that already exists elsewhere.

## 5. Provide a true quick-log flow

A default entry could be:

> Search → choose progress/status → save

Everything else is optional.

## 6. Support retroactive logging

People will often forget to log something immediately. Make entries easy to backdate and allow approximate dates such as:

- Earlier today
- Yesterday evening
- Sometime in June 2024
- Summer 2018
- Exact date unknown

Uncertain dates are particularly important if users want to reconstruct years of media history.

---

# The timeline could be the signature feature

The timeline should not look like an ordinary social feed. It should feel like a **visual autobiography**.

Possible views:

- **Chronological stream:** individual sessions and completed works
- **Day view:** everything consumed during a day
- **Calendar heatmap:** media activity over months and years
- **Zoomable timeline:** move from years to months to individual sessions
- **Media lanes:** parallel tracks for books, movies, games, music, and live events
- **Story mode:** “Your media life in 2026”
- **Memory resurfacing:** “Five years ago today…”
- **Location map:** media consumed at home, while traveling, or at venues
- **People view:** media experienced with a particular friend
- **Life chapters:** school, moves, relationships, trips, or user-defined periods

Visually, each medium should be immediately recognizable through restrained color, iconography, and card shape without making the interface chaotic.

---

# Important product decisions

## Keep ratings secondary

Ratings are useful, but emphasizing them too much can turn the app into a review platform. The more distinctive focus is **memory and context**.

Consider supporting several lightweight reactions:

- Numeric or star rating
- Favorite
- Emotional reaction
- Would recommend
- Short review

A rating should not be required.

## Allow repeats naturally

Rewatches, rereads, and replaying games should be first-class behavior—not duplicate-data edge cases.

The same movie might have:

- One media record
- Several releases or versions
- Five viewing sessions
- Three completed watches
- Different companions and ratings each time

## Treat privacy seriously

Locations, dates, companions, and personal notes can be sensitive. The product should be private by default, with granular sharing controls later.

Potential visibility levels:

- Private
- Visible to selected friends
- Visible to followers
- Public

## Avoid forcing everything into one taxonomy

Some experiences overlap:

- A filmed musical could be a movie or theater recording.
- An audiobook is both a book edition and an audio production.
- A live podcast is both a podcast and an event.
- A visual novel is both literature and a game.

Allow a primary type plus flexible tags or secondary classifications.

---

# Recommended initial product focus

The full vision is large. I would begin with five categories:

1. Movies
2. TV
3. Books/audiobooks
4. Video games
5. Live events

For the first version, focus on three actions:

- **Log an experience**
- **Browse your media library**
- **Explore your timeline**

I would deliberately postpone:

- Public social feeds
- Complex recommendations
- Comments and likes
- Advanced AI analysis
- Heavy gamification
- Support for every obscure medium

The goal of the first version should be proving that logging feels effortless and that the resulting timeline feels valuable.

---

# A polished product statement

> A private personal media journal that records not only what you watch, read, play, and attend, but the story surrounding each experience—when and where it happened, who shared it with you, which version you experienced, and what it meant to you.

A shorter version:

> **Your life, remembered through media.**

The strongest version of this idea is not “Letterboxd for everything.” It is closer to a **personal memory system centered on culture and entertainment**. That framing gives the project a clearer identity and supports the contextual details that make it unique.

*(34.32 seconds)*

**USER:** ok lets start with just movies and tv shows. create a new file in the website directory that has a detailed but still readble (not too long) spec for the app for these 2 media types

> TOOL: `list_dir(path='.')` -> '(empty directory)'

> TOOL: `write(path='PROJECT_SPEC.md', content="# Personal Movie & TV Tracker — Product Specification\n\n## 1. Product Summary\...')` -> "Created 'PROJECT_SPEC.md'"

> TOOL: `read(path='PROJECT_SPEC.md', start_line=1)` -> '0001| # Personal Movie & TV Tracker — Product Specification'

**AGENT:** Created `PROJECT_SPEC.md` in the website directory.

It includes:

- Product vision, goals, and MVP scope
- Movie and episode logging flows
- Optional contextual details and smart defaults
- Dashboard, library, title pages, timeline, and insights
- Visual design direction
- Recommended technical stack
- Initial relational database model
- Privacy and data-ownership requirements
- Clear MVP success criteria

I also reread the completed file to verify it was written correctly.

*(69.62 seconds)*

**USER:** i think the distinction between a media and experieinces is really powerful. All experieinces can be linked to the umbrella media so there can be multiple mdeia experieicens with a specific media. Going off od this, maybe instea dof the uer-title state, I want users to be abel to create watching goal that specific experieinces are addedd to so progress towards that goald can be tracked. For example, Say I watch to make a watching goal of watching the whole series Avatar the Last Airbender, the Watching goal will have all the episdoes listed, adn then as I go about wtahcing episodes, I can add those media experiences to that goal, adn theb goal can tell me how many epideos ive watch, how many more i have left, the percentage of how much i've accomplished the goal. But not all media experieinces will be part of goals, sometimes a person will just watch a movie or an epideos of a show and that should stil be tracked separetely and independtely of a goal. Does that make snese? How can i incorporate that into my idea?

**AGENT:** Yes, that makes excellent sense—and it strengthens the distinction between **media**, **experiences**, and **intentions**.

The clean conceptual model becomes:

> **Media is what exists. An experience is what happened. A goal is what the user intends to accomplish.**

These three concepts should remain independent but connected.

# The three core objects

## 1. Media

A media record represents the underlying work and its hierarchy:

```text
Avatar: The Last Airbender
├── Season 1
│   ├── Episode 1: The Boy in the Iceberg
│   ├── Episode 2: The Avatar Returns
│   └── ...
├── Season 2
└── Season 3
```

Movies generally have one directly consumable media item, while TV shows contain seasons and episodes.

A media record does not say whether a user has watched it. It only describes the work.

## 2. Media experience

A media experience records something the user actually did:

> Watched *Avatar: The Last Airbender*, S1E1, on October 9, 2026, at home with Alex on Netflix.

An episode can have multiple experiences:

- First watch
- Rewatch
- Partial watch
- Watching with different people
- Watching a different version or language

Experiences are always retained independently, whether or not they belong to a goal.

## 3. Watching goal

A watching goal describes a desired outcome and the media required to complete it.

For example:

```text
Goal: Watch all of Avatar: The Last Airbender

Includes:
- Season 1, Episodes 1–20
- Season 2, Episodes 1–20
- Season 3, Episodes 1–21

Progress:
- 14 of 61 episodes completed
- 23%
- 47 episodes remaining
```

The goal does not own the experiences. It references qualifying experiences and uses them as evidence of progress.

---

# Goals should contain media requirements

I would avoid directly placing experiences inside a goal as its fundamental structure. Instead:

1. A goal contains a list of required **media items**.
2. Experiences can be associated with those requirements.
3. The linked experiences determine whether each requirement has been completed.

Conceptually:

```text
Watching Goal
    ├── Goal Item: Episode 1
    │       └── Completed by Experience A
    ├── Goal Item: Episode 2
    │       └── Completed by Experience B
    └── Goal Item: Episode 3
            └── Not completed
```

This allows the app to know what remains before the user has watched it. If a goal only contained experiences, it could tell the user what they had done but not what they still needed to do.

# An experience can exist without a goal

This should be the normal relationship:

```text
Media → Experience
          └── Optional goal association
```

When logging an experience, the user should never be required to select a goal.

After selecting an episode or movie, the form could optionally show:

> **Counts toward:** Watch all of Avatar: The Last Airbender

If there is only one obvious matching goal, the app could select it automatically while allowing the user to remove the association.

# Automatic goal matching

Users should not need to manually add every relevant experience to a goal.

When an experience is logged, the app should:

1. Identify active goals containing that media item.
2. Check whether the experience satisfies the goal’s completion rules.
3. Suggest or automatically create the association.
4. Recalculate goal progress.

For example:

> You finished “The Avatar Returns.” This counts toward **Watch all of Avatar: The Last Airbender**. You have completed 2 of 61 episodes.

The user should still be able to exclude an experience from a goal. This matters when a person wants a goal to represent a particular watch-through.

---

# Goals need completion rules

Different goals may interpret the same experience differently.

## Example rules

A goal could require:

- Finishing each included movie or episode
- Watching any portion of each item
- Watching a certain number of episodes
- Rewatching items after the goal was created
- Watching items during a particular date range
- Watching a particular edition or version
- Watching with a specific person
- Watching on a particular platform
- Completing a target amount of viewing time

For the initial version, I recommend only two completion modes:

### Any historical experience

Past and future qualifying experiences count.

> “I want to track whether I have ever watched every Avatar episode.”

### New experiences only

Only experiences occurring after the goal begins count.

> “I want to rewatch all of Avatar this year.”

That distinction is essential. Otherwise, the system cannot tell whether a goal represents lifetime completion or a new watch-through.

# Goal types

The same model could support several useful goal structures.

## Complete a series

> Watch every episode of *Avatar: The Last Airbender*.

## Complete a season

> Watch Season 2 of *Severance*.

## Watch a collection or franchise

> Watch every James Bond movie.

## Complete a custom list

> Watch these ten horror movies during October.

## Reach a quantity

> Watch 50 movies in 2027.

## Time-based challenge

> Watch one movie each week for three months.

## Rewatch goal

> Rewatch all of *The Good Place* with Alex.

For the MVP, I would begin with:

- Complete a TV series
- Complete a TV season
- Watch a selected movie list
- Custom collection of movies and episodes

Quantity and recurring goals can come later because their progress logic is more complicated.

# How progress should be calculated

Progress should normally count **unique required media items completed**, not the total number of experiences.

If the user watches Episode 1 three times, the goal should still show:

```text
1 of 61 episodes completed
```

It should not show three completed episodes.

A simple calculation is:

```text
progress = completed goal items / total goal items
```

For example:

```text
14 completed episodes / 61 required episodes = 22.95%
```

The interface could show:

- `14 of 61 episodes`
- `23% complete`
- `47 remaining`
- Estimated remaining runtime
- Current season
- Last goal activity
- Current streak, if relevant

A goal may also preserve the experiences that counted, so the user can inspect exactly when and how each requirement was completed.

# Media hierarchy and goal expansion

Users should be able to add a whole show or season without manually selecting every episode.

If a user adds:

> *Avatar: The Last Airbender*

The system expands it into its currently known episodes as individual goal items.

Likewise:

```text
Add Season 1
```

becomes:

```text
Goal Item: S1E1
Goal Item: S1E2
Goal Item: S1E3
...
```

This provides episode-level progress while keeping goal creation simple.

You will need to decide how goals respond when new episodes are released. A goal could have one of two scope modes:

- **Snapshot:** Include only episodes known when the goal was created.
- **Dynamic:** Automatically include newly released episodes.

For completed shows like *Avatar*, there is no practical difference. For an active show, the distinction is important.

# Replace user-title state with derived information

I agree that a permanent `user-title state` becomes less important with this model.

Instead of requiring users to label every title as “watching” or “completed,” the app can derive useful information from experiences:

- Last watched date
- Episodes experienced
- Episodes finished
- Latest episode reached
- Percentage of the series ever watched
- Number of rewatches
- Whether there is an unfinished experience
- Whether the title belongs to an active goal

However, **Want to watch** still represents intention rather than viewing history. That can be handled through:

- A simple watchlist, or
- A lightweight watching goal

I would keep the watchlist separate because saving a movie for later should not require creating a formal goal.

# Recommended database relationships

The model could include:

```text
media_titles
tv_seasons
tv_episodes

media_experiences

watching_goals
watching_goal_items
experience_goal_matches
```

## `watching_goals`

Stores the goal itself:

- User
- Name
- Description
- Status: draft, active, paused, completed, abandoned
- Start date
- Optional target date
- Historical experiences count or new experiences only
- Snapshot or dynamic scope
- Created date
- Completed date

## `watching_goal_items`

Stores what must be consumed:

- Goal
- Movie or episode
- Required completion type
- Sort order
- Optional status override
- Added date

## `experience_goal_matches`

Associates an experience with a goal requirement:

- Experience
- Goal item
- Match source: automatic or manual
- Counts toward completion
- Matched date

Keeping the association in a separate table allows:

- One experience to count toward multiple goals
- One goal item to have multiple experiences
- Replacing the experience that completed an item
- Excluding an automatically matched experience
- Preserving an audit trail

# Interface changes

## Goals page

Add a main **Goals** section containing:

- Active goals
- Recently completed goals
- Paused goals
- Create goal button
- Overall progress cards

A goal card might display:

```text
Avatar: The Last Airbender

14 of 61 episodes
█████░░░░░░░░░░░░░ 23%

47 episodes remaining
Last activity: October 9
```

## Goal detail page

A goal’s page should contain:

- Goal name and artwork
- Progress bar
- Completed and remaining counts
- Estimated time remaining
- Target date
- Season or collection breakdown
- Required media checklist
- Experiences that contributed to progress
- Suggested next item
- Edit, pause, or abandon controls

## Experience form

When logging an experience, include an optional field:

```text
Counts toward goals

☑ Watch all of Avatar
☐ Watch 100 TV episodes this year
```

Matching goals should be suggested automatically.

## Timeline

Timeline cards can display a small goal indicator:

> Advanced **Watch all of Avatar** to 23%.

The experience should still appear normally even if the goal is later deleted.

# The refined product model

The application’s central model can now be summarized as:

```text
MEDIA
What can be watched

EXPERIENCE
What the user actually watched

GOAL
What the user intends to watch

GOAL ITEM
What must be completed

MATCH
Which experience satisfies which goal item
```

This is a much stronger foundation than storing a single status on every title. It preserves the factual history of what happened while allowing users to organize selected experiences into purposeful watch-throughs and challenges.

*(32.77 seconds)*

**USER:** I agree, a separete watchlist feature should just be a simple list of future media a suer wants to consume, that perhaps can be easily converted to a goal when deisred (especially useful for tv shows). So then goals can have different sates to them, the main ones being "in progress" and "completed". But when a goal is "in progress" i think the idea of have another layer of state specification that can being "actively watching", "pasued" or "dropped". to better filter and declutter a user's viewing experience. based on what you just said and theese new idea i'm saying now, read the spec aagin, and work out a  plan to rework the spec and tell me the spec before writing to the filet

> TOOL: `read(path='PROJECT_SPEC.md', start_line=1)` -> '0001| # Personal Movie & TV Tracker — Product Specification'

**AGENT:** I reread the current `PROJECT_SPEC.md`. The new model fits well, but it requires more than adding a Goals section—the spec’s core concepts, interface, logging flow, and database model should all be updated together.

I have **not edited the file yet**.

# Recommended product model

The revised app should center on four distinct concepts:

## 1. Media

The movie, TV series, season, or episode that exists independently of the user.

## 2. Media experience

A record of something the user watched:

- Watching an entire movie
- Watching part of a movie
- Watching an episode
- Rewatching something
- Watching the same episode with someone else

Experiences are factual history. They do not require a watchlist entry or goal.

## 3. Watchlist

A lightweight list of media the user may want to watch in the future.

A watchlist entry:

- Does not track progress
- Does not require a start date
- Does not create episode requirements
- Can be removed after watching
- Can be converted into a watching goal

This keeps “I might watch this someday” separate from “I am intentionally trying to complete this.”

## 4. Watching goal

A structured intention containing specific movies or episodes that must be completed.

A goal contains **goal items**, and qualifying media experiences satisfy those items.

For example:

```text
Goal: Watch Avatar: The Last Airbender

61 required episodes
17 completed
44 remaining
28% complete
```

# Refining the goal states

I agree with the need to declutter inactive goals, but I would slightly refine the state hierarchy.

Putting `dropped` beneath `in progress` creates a semantic conflict: a dropped goal is no longer in progress. A cleaner model is:

## Goal lifecycle status

- **In progress**
- **Completed**
- **Dropped**

## Activity state

Only applies when the lifecycle is `in progress`:

- **Actively watching**
- **Paused**

This produces the following valid combinations:

```text
In progress
├── Actively watching
└── Paused

Completed

Dropped
```

This is easier to reason about and implement than:

```text
In progress
├── Active
├── Paused
└── Dropped
```

## How this appears in the interface

The user does not need to see technical terms such as “lifecycle status.” The Goals page could simply have:

- **Active**
- **Paused**
- **Completed**
- **Dropped**

Active goals appear prominently. Paused goals appear in a collapsed section. Completed and dropped goals are archived by default.

This provides the decluttering you want while retaining a logically clean data model.

# Planned changes to the specification

## 1. Rewrite the product summary

The summary will explicitly establish that the app tracks:

- Media that exists
- Experiences that happened
- Future media saved to a watchlist
- Intentional viewing organized into goals

The core product statement will become approximately:

> A private personal movie and TV journal that records individual viewing experiences, organizes viewing history under shared media, and optionally connects those experiences to structured watching goals.

## 2. Update the product goals

I will add goals covering:

- Keeping experiences independent from goals
- Making watchlists lightweight
- Supporting structured viewing goals
- Automatically connecting experiences to relevant goals
- Measuring goal progress without counting repeated viewings as separate requirements
- Keeping inactive goals out of the main viewing workflow

## 3. Update the MVP scope

The included scope will gain:

- Movie and TV watchlists
- Watching goals
- Goal progress
- Active, paused, completed, and dropped goal views
- Watchlist-to-goal conversion
- Automatic experience-to-goal matching
- Manual inclusion and exclusion of experiences

More advanced goals will remain outside the initial release:

- Recurring weekly goals
- “Watch 100 movies” quantity challenges
- Social or shared goals
- Competitive challenges
- Complex conditional goal rules

The MVP will focus on goals made from specific movies and episodes.

# Revised core concepts section

The existing concepts will be reorganized into:

1. **Media**
2. **Media hierarchy**
3. **Release or edition**
4. **Media experience**
5. **Watchlist entry**
6. **Watching goal**
7. **Goal item**
8. **Experience-goal match**

The current `User-title state` section will be removed.

Instead of manually assigning every title a global status, the app will derive information such as:

- Previously watched
- Currently unfinished
- Number of times watched
- Latest episode experienced
- Percentage of episodes historically completed
- Part of an active goal
- Saved to the watchlist

This avoids conflicts when the same show appears in multiple goals or watch-throughs.

# Revised goal behavior

## Goal composition

A goal will contain one or more required media items.

Examples:

- One TV series, expanded into all episodes
- One season, expanded into its episodes
- A custom selection of episodes
- A list of movies
- A combination of movies and TV episodes

The app will automatically expand a selected series or season into episode-level goal items.

## Goal history rules

A goal will specify whether it counts:

- **All qualifying experiences:** Previous watches may immediately satisfy goal items.
- **New experiences only:** Only experiences on or after the goal’s start date count.

This supports both:

> Track whether I have ever watched all of Avatar.

and:

> Rewatch all of Avatar beginning today.

## Goal scope

TV goals will also define whether their episode list is:

- **Snapshot:** Only episodes known when the goal was created.
- **Dynamic:** New episodes are automatically added.

Snapshot will likely be the safest MVP default, with dynamic scope offered for currently airing shows.

## Goal progress

Progress will be calculated using unique goal items:

```text
completed goal items / total goal items
```

Watching one episode three times still completes only one episode requirement.

Goals may display:

- Items completed
- Items remaining
- Percentage complete
- Estimated runtime remaining
- Last activity
- Suggested next episode
- Progress by season

# Revised logging flow

The quick-log flow will remain fast and goal-independent:

1. Select media.
2. Select the viewing action.
3. Confirm the date and time.
4. Save.

If the selected media matches one or more active goals, the form will show an optional suggestion:

```text
Counts toward:

☑ Watch Avatar: The Last Airbender
☐ Watch 100 Favorite Episodes
```

The app may automatically select an obvious match, but users can remove it.

After saving, the confirmation may say:

```text
Experience saved

“Winter Solstice, Part 1” completed
Avatar goal: 7 of 61 episodes · 11%
```

An experience that does not match a goal is saved normally without any extra steps.

# Watchlist behavior

The specification will add the following watchlist rules:

- Users can save movies, shows, seasons, or individual episodes.
- Adding something to the watchlist does not create a goal.
- Logging an experience does not require the media to be on the watchlist.
- Watched entries may be automatically removed or retained, based on user preference.
- TV shows can be converted into goals.
- Multiple watchlist entries can be selected and converted into one custom goal.

For example:

```text
Watchlist entry:
Avatar: The Last Airbender

Actions:
- Log an experience
- Create “Watch entire series” goal
- Create goal from selected seasons
- Remove from watchlist
```

Movies can also become goals, especially as part of a custom collection:

```text
Select five watchlist movies
→ Create goal
→ “October Horror Movies”
```

# Interface changes

## Home dashboard

The dashboard will include:

- Log an experience
- Continue an unfinished experience
- Active goals
- Suggested next episodes
- Recent experiences
- Watchlist preview
- Timeline preview

Paused goals will not appear in the main active-goal area.

## Watchlist page

The new Watchlist page will provide:

- Movies and TV tabs
- Grid and list views
- Filters and sorting
- Multi-select
- Create a goal from selected items
- Remove entries
- Log an experience directly
- Convert a TV show into a whole-series or selected-season goal

## Goals page

The new Goals page will be organized into:

- Active
- Paused
- Completed
- Dropped

Each goal card will show:

- Artwork and title
- Progress bar
- Completed and remaining items
- Percentage
- Last activity
- Next suggested item
- Target date, if present

## Goal detail page

A goal detail page will contain:

- Goal title, description, and artwork
- Current state
- Start and optional target dates
- Progress summary
- Required media checklist
- Season breakdown for TV goals
- Experiences that contributed to progress
- Remaining runtime estimate
- Suggested next item
- Controls to pause, resume, complete, drop, or edit the goal

## Media detail pages

Movie and TV pages will show:

- All experiences involving the media
- Whether it is on the watchlist
- Goals containing it
- Historical viewing progress
- Quick actions to log, add to watchlist, or create a goal

The current “user status” field will be removed from these pages.

## Timeline

Experiences will remain the central timeline entries.

When applicable, an entry can also display:

```text
Advanced “Watch Avatar” to 28%
```

Deleting, completing, or dropping a goal will not delete or alter the underlying experience.

# Database changes

The current database section contains `viewing_sessions` and `user_title_states`. I plan to:

- Rename `viewing_sessions` to `media_experiences`
- Remove `user_title_states`
- Add watchlist and goal tables

The revised core tables will be:

```text
users

media_titles
tv_seasons
tv_episodes
releases

media_experiences

watchlist_entries

watching_goals
watching_goal_items
experience_goal_matches

locations
people
media_experience_people

providers
reaction_tags
media_experience_reactions
```

## `watchlist_entries`

Important fields:

- User
- Media item
- Date added
- Optional note
- Priority
- Created source
- Sort order

A unique constraint should prevent the same media item from being accidentally added to a user’s watchlist multiple times.

## `watching_goals`

Important fields:

- User
- Name
- Description
- Lifecycle status
- Activity state
- Start date
- Optional target date
- Historical or new-experiences-only rule
- Snapshot or dynamic scope
- Completed date
- Dropped date
- Created and updated timestamps

Example state rules:

```text
lifecycle_status = IN_PROGRESS
activity_state = ACTIVE | PAUSED

lifecycle_status = COMPLETED
activity_state = null

lifecycle_status = DROPPED
activity_state = null
```

## `watching_goal_items`

Important fields:

- Goal
- Required movie or episode
- Sort order
- Added date
- Optional manual completion override
- Completion date

## `experience_goal_matches`

Important fields:

- Experience
- Goal item
- Match source: automatic or manual
- Counts toward completion
- Match date

An experience may count toward multiple goals, but each unique goal item counts only once toward that goal’s percentage.

# Updated MVP success criteria

The revised MVP criteria will add the ability to:

1. Add movies and shows to a simple watchlist.
2. Create a goal from a show, season, or custom media selection.
3. Convert watchlist entries into a goal.
4. Log experiences without assigning them to goals.
5. Automatically match experiences to relevant goals.
6. Manually include or exclude an experience from a goal.
7. View goal progress by item, season, count, and percentage.
8. Pause and resume an in-progress goal.
9. Complete or drop a goal without altering its experiences.
10. Filter goals into active, paused, completed, and dropped views.

# Sections that will remain mostly unchanged

These portions of the current spec need little or no modification:

- Visual design direction
- Technical stack
- External metadata approach
- Privacy principles
- Contextual experience fields
- Timeline modes
- General insights

The main terminology will change from **viewing session** to **media experience** throughout the document because that better reflects the product’s central idea.

This revision will make the architecture clearly express:

```text
Media       = what exists
Experience  = what happened
Watchlist   = what might be watched
Goal        = what the user intends to complete
Goal item   = what the goal requires
Match       = how an experience advances a goal
```

*(39.67 seconds)*

**USER:** ok, now make a new spec and call it spec2.0 with the newly designed spec

> TOOL: `write(path='SPEC2.0.md', content="# Personal Movie & TV Tracker — Specification 2.0\n\n## 1. Product Summary\n\nA...')` -> "Created 'SPEC2.0.md'"

> TOOL: `read(path='SPEC2.0.md', start_line=1)` -> '0001| # Personal Movie & TV Tracker — Specification 2.0'

> TOOL: `read(path='SPEC2.0.md', start_line=401)` -> '0401| - Total estimated viewing time'

**AGENT:** Created and verified the revised specification:

- **New file:** `SPEC2.0.md`
- **Original preserved:** `PROJECT_SPEC.md`

The new spec incorporates:

- Media versus media experiences
- Independent watchlists
- Watchlist-to-goal conversion
- Goal items and experience-goal matching
- Active, paused, completed, and dropped goal states
- Historical versus new-experience goal rules
- Snapshot versus dynamic TV goals
- Updated logging and goal-matching flows
- Watchlist and Goals interfaces
- Revised database model
- Updated privacy rules and MVP criteria

*(61.68 seconds)*

**USER:** ok, i'm trying to think  about how I'm actually going to store media data in the media entities. And how I'm even going to get that data. IS there some sort of api for amovies and tv show information, perhaps on imdb, that I can hook up to to get information for a speicif media? Thies way when the user creates a goal to watch all of avater, the api call can just go and grab the episdoe count and data?

> TOOL: `web_search('site:developer.themoviedb.org API TV series details seasons episodes official', 'site:developer.imdb.com official IMDb API documentation pricing datasets', 'site:tvmaze.com/api official TVmaze API show episodes', 'site:omdbapi.com official OMDb API documentation')`

> TOOL: `web_search('site:developer.themoviedb.org/reference tv-series-details season details movie details TMDB', 'site:developer.themoviedb.org/docs getting started authentication rate limiting attribution', 'site:developer.imdb.com documentation API GraphQL IMDb pricing Amazon Data Exchange', 'site:omdbapi.com API poster episode season documentation pricing')`

> TOOL: `web_search('site:developer.themoviedb.org/docs FAQ attribution commercial use TMDB API official', 'site:themoviedb.org/api-terms-of-use TMDB API terms official', 'site:developer.themoviedb.org/reference/tv-series-details number_of_episodes seasons', 'site:developer.themoviedb.org/reference/search-movie official')`

> TOOL: `web_search('site:developer.imdb.com non-commercial datasets IMDb official title episode TSV', 'site:developer.imdb.com imdb api graphql official docs title episodes', 'site:developer.imdb.com pricing IMDb API Amazon Data Exchange', 'site:developer.imdb.com imdb datasets title.episode.tsv official')`

> TOOL: `web_search('IMDb datasets non commercial use official interfaces title.episode.tsv.gz', 'site:help.imdb.com interfaces datasets non-commercial use IMDb', 'site:developer.imdb.com "Non-Commercial" IMDb datasets')`

> TOOL: `web_search('site:developer.themoviedb.org/reference/tv-series-details "number_of_episodes"', 'site:developer.themoviedb.org/reference/tv-series-details "seasons"', 'site:developer.themoviedb.org/reference/tv-episode-details official')`

**AGENT:** Yes—this is exactly what a movie/TV metadata API is designed to solve.

## Best choice for this app: TMDB

For the MVP, I recommend using **The Movie Database API (TMDB)** rather than IMDb.

TMDB supports:

- Movie and TV search
- Movie details
- TV series and season details
- Episode names, numbers, runtimes, air dates, summaries, and images
- Posters and backdrops
- Cast and crew
- Movie collections
- External IDs, including IMDb IDs

The common TMDB workflow is to search for a title and then request its detailed information using the returned TMDB ID. Its season-details endpoint returns the episodes belonging to that season. ([developer.themoviedb.org](https://developer.themoviedb.org/docs/search-and-query-for-details?utm_source=openai))

TMDB uses an application API token, which should be kept on your server and sent as a Bearer token. ([developer.themoviedb.org](https://developer.themoviedb.org/docs/authentication-application?utm_source=openai))

# Example: creating an Avatar goal

When a user searches for “Avatar: The Last Airbender,” your application would do this:

## 1. Search TMDB

```http
GET /3/search/tv?query=Avatar%20The%20Last%20Airbender
```

The response contains possible matches with:

- TMDB ID
- Name
- First-air date
- Description
- Poster
- Original language

The user selects the correct series.

## 2. Import the series

Using the selected TMDB ID, your backend requests the series details and obtains its general metadata and season list.

Conceptually:

```http
GET /3/tv/{tmdbSeriesId}
```

## 3. Import each season and its episodes

For every included season:

```http
GET /3/tv/{tmdbSeriesId}/season/{seasonNumber}
```

The season response includes an `episodes` array containing details such as:

- TMDB episode ID
- Season number
- Episode number
- Episode name
- Air date
- Runtime
- Description
- Still-image path
- Episode type

TMDB’s official season endpoint returns the season’s episode objects directly. ([developer.themoviedb.org](https://developer.themoviedb.org/reference/tv-season-details?utm_source=openai))

## 4. Save the hierarchy locally

Your database stores:

```text
Avatar: The Last Airbender
├── Season 1
│   ├── Episode 1
│   ├── Episode 2
│   └── ...
├── Season 2
└── Season 3
```

## 5. Generate the goal items

After the episodes have been imported, your app creates one goal item for every included episode:

```text
Goal: Watch Avatar: The Last Airbender

Goal Item 1 → S1E1
Goal Item 2 → S1E2
Goal Item 3 → S1E3
...
```

The total number of goal items becomes the goal’s denominator:

```text
completed goal items / total goal items
```

You should import the actual episodes rather than storing only an episode count. Otherwise, the app could say “17 of 61” but would not know which 17 were completed.

# Store metadata locally

Do not call TMDB every time a user opens a title page. Treat TMDB as an **external metadata source**, not your live application database.

The recommended flow is:

```text
TMDB
  ↓ import/synchronize
Your media database
  ↓ referenced by
Experiences, watchlist entries, and goals
```

Your database becomes the source of truth for:

- User experiences
- Watchlist entries
- Goals
- Goal items
- Ratings
- Notes
- Companions
- Locations

TMDB remains the source for:

- Titles
- Posters and backdrops
- Seasons and episodes
- Release and air dates
- Runtime
- Genres
- Cast and crew
- General descriptions

# Suggested media schema

I would modify the media side of the schema to look approximately like this.

## `media_titles`

Stores movies and TV series:

```text
id
media_type                 MOVIE | TV_SERIES

title
original_title
overview
original_language

release_date
first_air_date
last_air_date

runtime_minutes
status

poster_path
backdrop_path

tmdb_id
imdb_id

metadata_source
metadata_last_synced_at

created_at
updated_at
```

Use a unique constraint on:

```text
metadata_source + external ID
```

For example:

```text
TMDB + 246
```

That prevents two users importing the same show from creating duplicate media records.

## `tv_seasons`

```text
id
series_id
season_number
name
overview
air_date
episode_count
poster_path

tmdb_id
metadata_last_synced_at
```

Recommended unique constraint:

```text
series_id + season_number
```

## `tv_episodes`

```text
id
series_id
season_id

season_number
episode_number
episode_type

title
overview
air_date
runtime_minutes
still_path

tmdb_id
metadata_last_synced_at

created_at
updated_at
```

Recommended unique constraints:

```text
tmdb_id
```

and:

```text
series_id + season_number + episode_number
```

## `media_external_ids`

Instead of putting every possible provider ID directly on `media_titles`, you could use a flexible table:

```text
id
media_title_id
provider
external_id
```

Example records:

```text
Avatar | TMDB  | 246
Avatar | IMDB  | tt0417299
Avatar | TVDB  | 74852
```

This makes it easier to change providers or combine data sources later.

For episodes, you may eventually want a corresponding:

```text
episode_external_ids
```

But a direct `tmdb_id` column is sufficient for the MVP.

# Import only what the app needs

Avoid copying every field returned by TMDB. Some responses contain far more information than your product requires.

For the first version, store:

## Movie

- TMDB ID
- Title and original title
- Overview
- Release date
- Runtime
- Poster and backdrop paths
- Genres
- Original language
- Collection ID, if applicable
- IMDb ID, when available

## TV series

- TMDB ID
- Name and original name
- Overview
- First and last air dates
- Series status
- Poster and backdrop paths
- Genres
- Original language
- Season count
- Episode count

## Season

- Season number
- Name
- Air date
- Poster
- Episode count

## Episode

- TMDB episode ID
- Season and episode numbers
- Name
- Overview
- Air date
- Runtime
- Still-image path
- Episode type

Cast and crew can be added later. Your central product does not require a complete entertainment-industry database.

# Handling specials

TV APIs commonly represent specials as **Season 0**. You should not automatically include them in an “entire series” goal without asking.

When creating a goal, provide:

```text
Include in this goal:

☑ Season 1
☑ Season 2
☑ Season 3
☐ Specials
```

Recommended default:

- Include numbered seasons
- Exclude Season 0 and specials
- Allow the user to include specific specials manually

Also pay attention to TMDB’s `episode_type`, because not every episode-like record is necessarily a standard episode. The season response includes this field. ([developer.themoviedb.org](https://developer.themoviedb.org/reference/tv-season-details?utm_source=openai))

# Snapshot and dynamic goals

The API integrates neatly with the snapshot/dynamic distinction already in the spec.

## Snapshot goal

At creation time:

1. Import all known episodes.
2. Create fixed goal items.
3. Do not automatically add future episodes.

## Dynamic goal

At creation time:

1. Import all known episodes.
2. Create the initial goal items.
3. Periodically synchronize the series.
4. Add newly discovered episodes as goal items.

For active series, synchronization might occur:

- When a user opens the goal
- When they log an experience for the series
- Once per day through a background job
- When the stored metadata is older than a configured threshold

You do not need real-time synchronization.

# Recommended service abstraction

Even if you begin with TMDB, do not scatter direct TMDB calls throughout the application. Create an internal metadata-provider layer:

```ts
interface MediaMetadataProvider {
  searchMovies(query: string): Promise<MovieSearchResult[]>;
  searchSeries(query: string): Promise<SeriesSearchResult[]>;

  getMovie(providerId: string): Promise<MovieMetadata>;
  getSeries(providerId: string): Promise<SeriesMetadata>;
  getSeason(
    seriesProviderId: string,
    seasonNumber: number
  ): Promise<SeasonMetadata>;
}
```

Then implement:

```ts
class TmdbMetadataProvider implements MediaMetadataProvider {
  // TMDB-specific requests and response mapping
}
```

The rest of your application should call functions such as:

```ts
searchMedia(query);
importMovie(tmdbId);
importSeries(tmdbId);
syncSeries(localSeriesId);
```

That makes it possible to add or switch to TVmaze, IMDb, or another provider later without rewriting goal and experience logic.

# What about IMDb?

IMDb now offers official commercial metadata products and APIs through AWS Data Exchange. Its developer offering is positioned as licensed metadata rather than a simple free API for small applications. ([developer.imdb.com](https://developer.imdb.com/?rf=mProPublic&utm_source=openai))

IMDb also publishes daily non-commercial TSV datasets. These include:

- Basic title information
- Ratings
- Crew
- Cast
- Episode-to-series relationships
- Season and episode numbers

However, these are bulk compressed data files rather than a convenient title-search API. IMDb permits limited personal and non-commercial use under its dataset terms and does not permit scraping the IMDb website. ([imdb.com](https://www.imdb.com/interfaces/?source=post_page---------------------------&utm_source=openai))

You could use those files, but that would require:

- Downloading large datasets
- Importing them into your database
- Building your own search
- Refreshing the files regularly
- Joining several datasets
- Handling stricter usage restrictions

That is unnecessary complexity for your MVP.

# Alternative: TVmaze

TVmaze is a good alternative specifically for TV. Its free public API can search shows and return an entire show’s episode list in one response using `embed=episodes`. It also exposes dedicated show, season, episode, and alternate-order endpoints. ([tvmaze.com](https://www.tvmaze.com/api?utm_source=openai))

Advantages:

- Very simple API
- Entire episode list available in one request
- Free public access
- Useful alternate episode orders

Disadvantages:

- TV only—no movies
- Less comprehensive artwork and movie-oriented metadata
- Free API uses a CC BY-SA license requiring attribution and ShareAlike compliance
- The free service has published request limits and no SLA ([tvmaze.com](https://www.tvmaze.com/api?utm_source=openai))

Because your application covers both movies and TV, TMDB provides a cleaner single-provider starting point.

# Important licensing consideration

TMDB’s API is free for non-commercial projects with required attribution. Its official attribution includes displaying the TMDB logo and a notice explaining that TMDB does not endorse or certify the application. Commercial use requires a separate written agreement. ([developer.themoviedb.org](https://developer.themoviedb.org/docs/faq?utm_source=openai))

TMDB’s current API terms also restrict caching its information for longer than six months, so you should store a `metadata_last_synced_at` value and refresh imported metadata periodically. User-created records must stay separate so a metadata refresh never affects experiences or goals. ([themoviedb.org](https://www.themoviedb.org/api-terms-of-use?utm_source=openai))

# My recommendation

Use:

```text
TMDB API
    ↓
Server-side metadata-provider service
    ↓
Local PostgreSQL media records
    ↓
Watchlists, goals, goal items, and experiences
```

The goal-creation process becomes:

```text
User selects a series
        ↓
Find or import its local media record
        ↓
Fetch seasons and episodes from TMDB
        ↓
Upsert seasons and episodes locally
        ↓
Let the user select seasons and specials
        ↓
Create one goal item per selected episode
        ↓
Calculate progress from matching experiences
```

This gives you enough information to create the complete Avatar goal automatically while keeping the user’s experiences and goals safely under your own application’s control.

*(61.92 seconds)*

**Sources:**
1. [Search & Query For Details](https://developer.themoviedb.org/docs/search-and-query-for-details?utm_source=openai)
2. [Application](https://developer.themoviedb.org/docs/authentication-application?utm_source=openai)
3. [Details](https://developer.themoviedb.org/reference/tv-season-details?utm_source=openai)
4. [IMDb — The World's Most Authoritative Entertainment Data](https://developer.imdb.com/?rf=mProPublic&utm_source=openai)
5. [IMDb Non-Commercial Datasets | IMDb Developer](https://www.imdb.com/interfaces/?source=post_page---------------------------&utm_source=openai)
6. [TV API | TVmaze - Add TV information to your website or app.](https://www.tvmaze.com/api?utm_source=openai)
7. [FAQ](https://developer.themoviedb.org/docs/faq?utm_source=openai)
8. [API Terms of Use — The Movie Database (TMDB)](https://www.themoviedb.org/api-terms-of-use?utm_source=openai)

**USER:** so in terms of scalability and personal data storage, lets say my media entity table is going to be dyantically added to whenver a user watches a new show or movie, since then my database with use the tmb api to fetch that medias info, store it in a table and then any user can make an experieince or a goal with that data without causing another api call. i thinkn this model would work but we'd have to distinguish ebtween past media and still realsing media (at least for tv shows). Tv showes that aren't airing any more dont need to be updated  (except for eveyr 6 motnhs accoridng to the api) but new shows with newly weekly epideos should update after every new episode comes out, so perhaps the next airdate is stored and then whenever a user tries to access that new show, if the current date has passed the next air date, the api is called again to get the new data. Does this make sense? IS this a good way to go about it?

> TOOL: `web_search('site:developer.themoviedb.org/reference tv series details next_episode_to_air status last_air_date official', 'site:developer.themoviedb.org/reference tv-series-changes official TMDB changes', 'site:developer.themoviedb.org/docs tracking changes TMDB official', 'site:themoviedb.org/api-terms-of-use caching six months official')`

**AGENT:** Yes, the overall model is sound:

> **Import shared media once, store it centrally, and let every user reference the same media records.**

Your idea of tracking the next air date is also useful, but it should be **one refresh signal rather than the entire refresh strategy**.

# Recommended architecture

Keep global media data separate from personal user data:

```text
Shared catalog
├── Media titles
├── TV seasons
├── TV episodes
└── Releases

Personal data
├── Experiences
├── Watchlist entries
├── Goals
└── Goal items
```

If 10,000 users watch the same Avatar episode, you should have:

```text
1 episode record
10,000 user experience records
```

All experiences reference the same episode ID.

That is scalable, avoids duplicated metadata, and minimizes external API calls.

# Import media on demand

You do not need to import the entire TMDB catalog. Import media only when someone needs it.

For example:

1. The user searches TMDB for *Avatar*.
2. Your application checks whether the selected TMDB ID already exists locally.
3. If it exists, use the local media record.
4. If it does not exist, fetch it from TMDB and create the local series, seasons, and episodes.
5. Future users reuse those local records.

Pseudocode:

```ts
async function findOrImportSeries(tmdbId: number) {
  const existing = await db.mediaTitle.findUnique({
    where: {
      source_externalId: {
        source: "TMDB",
        externalId: String(tmdbId),
      },
    },
  });

  if (existing) {
    return existing;
  }

  return importSeriesFromTmdb(tmdbId);
}
```

Use a database unique constraint so simultaneous requests cannot create duplicate records:

```text
UNIQUE(metadata_source, external_id)
```

# Your next-air-date strategy

Your proposed sequence is reasonable:

```text
Store next air date
        ↓
User accesses series after that date
        ↓
Refresh series metadata
        ↓
Import newly available episodes
```

However, `next_air_date` should not be the only condition because:

- A planned air date may change.
- An episode may be postponed.
- Multiple episodes may release together.
- A newly announced episode might not have been present during the previous synchronization.
- Episode metadata may be incomplete when first added and filled in later.
- A show might return after having no known next air date.
- Existing metadata may be corrected even when no new episode airs.

Instead, store a general `next_sync_at` value. The next episode’s air date can help determine that value.

# Fields to store for synchronization

Add synchronization fields to `media_titles`:

```text
metadata_source
external_id

release_status
last_synced_at
next_sync_at
sync_state
sync_error_count
last_sync_error
```

For TV series, also store:

```text
next_episode_air_at
last_episode_air_at
```

Possible `sync_state` values:

```text
CURRENT
STALE
SYNCING
FAILED
```

You may not need `sync_state` in the first implementation, but `last_synced_at` and `next_sync_at` are essential.

# Use a hybrid refresh policy

I recommend combining three strategies:

1. Import on demand.
2. Refresh stale records when accessed.
3. Run a lightweight background synchronization job.

## Actively releasing shows

For an airing show:

- Synchronize when first imported.
- Store its next known air date.
- Set `next_sync_at` shortly after that air date.
- Mark it stale if TMDB reports that its data changed.
- Refresh active shows periodically as a fallback.

Example:

```text
next episode air date: October 12 at 9:00 PM
next sync: October 13 at 3:00 AM
```

Waiting several hours gives the metadata provider time to receive complete episode information.

## Shows with no known next episode

If the series is still active but has no known next episode:

```text
next_sync_at = last_synced_at + 7 days
```

The interval could later be made longer for shows between seasons.

## Ended or canceled shows

These do not need frequent synchronization:

```text
next_sync_at = last_synced_at + 5 months
```

TMDB’s terms currently say cached TMDB information cannot be retained for longer than six months, so setting the refresh period slightly below six months provides a safety margin. ([themoviedb.org](https://www.themoviedb.org/api-terms-of-use?utm_source=openai))

Even an ended series should eventually be refreshed because metadata, artwork, episode runtimes, translations, and other details may be corrected.

## Movies

A similar policy can apply to movies:

- Upcoming movie: refresh frequently as release approaches.
- Recently released movie: refresh every few weeks.
- Older movie: refresh approximately every five months.
- User-created experiences never need synchronization.

# Use TMDB’s change tracking

TMDB provides change endpoints specifically for synchronization. The TV change list identifies TV IDs changed during the previous 24 hours by default and can cover a period of up to 14 days. TMDB recommends using this system to keep metadata current. ([developer.themoviedb.org](https://developer.themoviedb.org/docs/tracking-content-changes?utm_source=openai))

At scale, a background worker can:

1. Request TMDB’s changed TV IDs.
2. Compare those IDs with the TMDB IDs in your local database.
3. Ignore titles you have never imported.
4. Mark matching local titles as stale.
5. Queue them for synchronization.

Conceptually:

```ts
const changedTmdbIds = await tmdb.getChangedSeriesIds();

const importedSeries = await db.mediaTitle.findMany({
  where: {
    source: "TMDB",
    externalId: {
      in: changedTmdbIds,
    },
  },
});

for (const series of importedSeries) {
  await syncQueue.add({
    mediaTitleId: series.id,
  });
}
```

This is more scalable than checking every locally stored title individually.

## Recommended combined policy

```text
TMDB change list
    → Detect imported titles that have changed

next_sync_at
    → Ensure nothing remains stale indefinitely

next_episode_air_at
    → Refresh promptly after an expected episode

user access
    → Trigger refresh if cached metadata is stale
```

# Do not block normal page access

Suppose a user opens a show and its metadata is due for synchronization. Avoid making them wait for several TMDB requests before rendering the page.

Use a stale-while-revalidate pattern:

1. Return the currently stored metadata.
2. Mark or detect that the record is stale.
3. Queue a background synchronization.
4. Update the page after synchronization or show the new data on the next request.

```ts
async function getSeries(localSeriesId: string) {
  const series = await db.mediaTitle.findUnique({
    where: { id: localSeriesId },
  });

  if (series.nextSyncAt <= new Date()) {
    await syncQueue.add(
      "sync-series",
      { seriesId: series.id },
      {
        jobId: `sync-series:${series.id}`,
      },
    );
  }

  return series;
}
```

Using the series ID as the queue job ID helps prevent hundreds of users from scheduling the same update simultaneously.

## Exception: goal creation

Creating a whole-series goal is one place where accuracy is important enough to wait for a refresh.

When the user creates a dynamic or snapshot goal:

1. Check whether the series metadata is current.
2. If stale, synchronize it.
3. Import all selected seasons and episodes.
4. Create the goal items.
5. Complete the transaction.

That avoids creating a snapshot goal from an outdated episode list.

# Synchronize incrementally

When updating a series, do not delete and recreate all its episodes.

Use provider IDs to upsert records:

```ts
await db.tvEpisode.upsert({
  where: {
    source_externalId: {
      source: "TMDB",
      externalId: String(tmdbEpisode.id),
    },
  },
  update: {
    title: tmdbEpisode.name,
    overview: tmdbEpisode.overview,
    airDate: tmdbEpisode.air_date,
    runtimeMinutes: tmdbEpisode.runtime,
    lastSyncedAt: new Date(),
  },
  create: {
    source: "TMDB",
    externalId: String(tmdbEpisode.id),
    seriesId,
    seasonId,
    seasonNumber: tmdbEpisode.season_number,
    episodeNumber: tmdbEpisode.episode_number,
    title: tmdbEpisode.name,
    overview: tmdbEpisode.overview,
    airDate: tmdbEpisode.air_date,
    runtimeMinutes: tmdbEpisode.runtime,
    lastSyncedAt: new Date(),
  },
});
```

TMDB’s season-details endpoint provides an episode array containing episode IDs, air dates, season and episode numbers, names, descriptions, runtimes, types, and image paths. ([developer.themoviedb.org](https://developer.themoviedb.org/reference/tv-season-details?utm_source=openai))

Using provider episode IDs lets metadata change without breaking:

- Existing experiences
- Goal-item references
- Watch history
- Ratings and notes

Your internal database ID remains stable even when imported fields change.

# Dynamic versus snapshot goals

Synchronization should affect each goal type differently.

## Dynamic goal

When new episodes are imported:

```text
Series synchronized
        ↓
New episodes discovered
        ↓
Create additional goal items
        ↓
Recalculate goal progress
```

For example:

```text
Before update: 7 of 8 episodes — 88%
New episode added: 7 of 9 episodes — 78%
```

You should notify the user when a completed or nearly completed goal expands:

> A new episode was added to “Watch the entire series.”

## Snapshot goal

New episodes should not be added automatically:

```text
Series synchronized
        ↓
New episode imported
        ↓
Snapshot goal remains unchanged
```

The user could receive an optional action:

> One new episode is available. Add it to this goal?

# Handling removed or renumbered episodes

External metadata can occasionally change in ways more complicated than adding an episode.

Do not hard-delete an imported episode if it disappears from a later API response, especially if user experiences reference it.

Instead, add fields such as:

```text
provider_visible
provider_last_seen_at
metadata_status
```

Possible status values:

```text
ACTIVE
MISSING_FROM_PROVIDER
MERGED
REMOVED
```

If an episode disappears from TMDB:

- Preserve the local record.
- Preserve experiences and goal items.
- Mark it as missing from the provider.
- Exclude it from newly created goals until reviewed.
- Never silently destroy personal history.

# Concurrency protection

Imagine a popular show releasing an episode and 500 users opening its page simultaneously. Without protection, they could all trigger the same API synchronization.

Use:

- A queue with unique job IDs
- A database or distributed lock
- A short synchronization cooldown
- Idempotent upserts

Example:

```text
sync-series:tmdb:12345
```

Only one active job with that key should exist at a time.

Your update procedure should be safe to run more than once.

# Recommended refresh schedule

A reasonable initial policy is:

```text
Actively airing, next episode known:
  Shortly after next_episode_air_at

Active, no next episode known:
  Every 7–14 days

Planned or in production:
  Every 7–14 days

Ended or canceled:
  Every 5 months

Upcoming movie:
  Every 7–14 days

Recently released movie:
  Every 30 days

Older movie:
  Every 5 months
```

These are application policies rather than requirements from TMDB. They can be adjusted once you observe actual API usage.

The six-month maximum cache period and requirement to avoid excessive bandwidth should both inform the final schedule. ([themoviedb.org](https://www.themoviedb.org/api-terms-of-use?utm_source=openai))

# One important licensing warning

Your technical architecture works, but the legal side needs attention before launching commercially.

TMDB’s current terms require attribution, prohibit retaining cached content longer than six months, and require a separate written agreement for commercial use. They also require cached TMDB content to be removed if API access terminates. ([themoviedb.org](https://www.themoviedb.org/api-terms-of-use?utm_source=openai))

Therefore, keep these data categories strictly separated:

```text
TMDB-derived metadata
├── Title
├── Overview
├── Artwork path
├── Episode metadata
└── Cast and crew

User-owned data
├── Experiences
├── Ratings
├── Notes
├── Goals
├── Goal progress
├── Locations
└── Companions
```

If you ever need to remove or replace TMDB-derived content, the user’s personal records remain intact.

# Final recommendation

Your model is good, with one adjustment:

> Store `next_episode_air_at`, but use it to calculate `next_sync_at` rather than making it the sole source of refresh decisions.

The complete strategy should be:

```text
Import on demand
        +
Store and reuse global media records
        +
Track last_synced_at and next_sync_at
        +
Refresh after known air dates
        +
Use TMDB's change list to detect edits
        +
Run infrequent fallback refreshes
        +
Serve stale data while refreshing in the background
        +
Synchronize before creating an episode-complete goal
```

This gives you low API usage, fast page loads, reliable goal creation, and a clean separation between shared metadata and personal user data.

*(50.03 seconds)*

**Sources:**
1. [API Terms of Use — The Movie Database (TMDB)](https://www.themoviedb.org/api-terms-of-use?utm_source=openai)
2. [Tracking Changes](https://developer.themoviedb.org/docs/tracking-content-changes?utm_source=openai)
3. [Details](https://developer.themoviedb.org/reference/tv-season-details?utm_source=openai)

**USER:** ok, use this data modeling and decisons we've made to update and edit parts of SPEC2.0

> TOOL: `edit(path='SPEC2.0.md', replace_this='### 4.1 Media\n\nMedia describes the underlying work independently of any user....', with_this="### 4.1 Media\n\nMedia describes the underlying work independently of any user....')` -> "Edited 'SPEC2.0.md'"

> TOOL: `edit(path='SPEC2.0.md', replace_this='### 5.3 Goal scope\n\nSeries and season goals use one of two scope rules:\n\n- ...', with_this='### 5.3 Goal scope\n\nSeries and season goals use one of two scope rules:\n\n- ...')` -> "Edited 'SPEC2.0.md'"

> TOOL: `edit(path='SPEC2.0.md', replace_this='### External metadata\n\nUse a movie and TV metadata provider for search, artwo...', with_this="### External metadata and shared catalog\n\nUse TMDB initially for movie and TV...')` -> "Edited 'SPEC2.0.md'"

> TOOL: `edit(path='SPEC2.0.md', replace_this='### Core tables\n\n- `users`\n- `media_titles` — movies and TV shows\n- `tv_sea...', with_this='### Core tables\n\n- `users`\n- `media_titles` — globally shared movies and TV ...')` -> "Edited 'SPEC2.0.md'"

> TOOL: `edit(path='SPEC2.0.md', replace_this='### Historical integrity\n\nProgress before and after an experience should be s...', with_this='### Historical integrity\n\nProgress before and after an experience should be s...')` -> "Edited 'SPEC2.0.md'"

> TOOL: `edit(path='SPEC2.0.md', replace_this='The first release is successful when a user can:\n\n1. Create an account and se...', with_this='The first release is successful when a user can:\n\n1. Create an account and se...')` -> "Edited 'SPEC2.0.md'"

> TOOL: `read(path='SPEC2.0.md', start_line=55)` -> '0055| - Other media types'

> TOOL: `read(path='SPEC2.0.md', start_line=430)` -> '0430| '

**AGENT:** Updated and verified `SPEC2.0.md`.

### Changes made

- Defined media entities as a **globally shared catalog**
- Added **on-demand TMDB importing and deduplication**
- Established stable local IDs independent of external API objects
- Added synchronization before creating series and season goals
- Defined handling for specials and Season 0
- Added dynamic versus snapshot goal update behavior
- Added a server-side metadata-provider abstraction
- Documented the shared-catalog import flow
- Added hybrid metadata synchronization using:
  - Next episode air dates
  - Scheduled refreshes
  - TMDB changed-title detection
  - Stale-while-revalidate
- Added concurrency protection and idempotent synchronization
- Defined handling for episodes removed from provider responses
- Expanded the database model with external IDs and synchronization fields
- Clarified separation between provider metadata and personal data
- Updated MVP success criteria to include importing, caching, synchronization, and accurate goal creation

The original `PROJECT_SPEC.md` remains unchanged.

*(147.48 seconds)*

```
----------- Usage ------------
~~~~~~~~~gpt-5.6-sol~~~~~~~~~~
Input (tokens): 705286
Cached (tokens): 605196
Output (tokens): 26136
Reasoning (tokens): 3374
gpt-5.6-sol cost (USD): $1.165158
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Total cost (USD): $1.165158
Web searches: 7
Web search cost (USD): $0.070000
```
