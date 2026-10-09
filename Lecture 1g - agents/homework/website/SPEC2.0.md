# Personal Movie & TV Tracker — Specification 2.0

## 1. Product Summary

A private-first media journal for recording movies and TV as personal experiences—not simply marking titles as watched.

The application separates four ideas:

- **Media:** What exists, such as a movie, show, season, or episode.
- **Media experience:** What the user actually watched and the context surrounding it.
- **Watchlist:** Media the user may want to watch in the future.
- **Watching goal:** A structured intention to complete a defined set of movies or episodes.

A media item can have many experiences. Experiences may advance one or more goals, but they remain valid and useful without a watchlist entry or goal.

**Product promise:** Logging an experience should take less than 15 seconds, while optional details, watchlists, and goals support deeper organization without adding friction.

## 2. Product Principles

- **Experiences are the source of truth.** The application records what happened rather than storing one permanent “watched” state on a title.
- **Intent is separate from history.** Watchlists and goals describe future intentions; experiences describe actual viewing.
- **Goals are optional.** Users can log any movie or episode without first organizing it.
- **Details are progressive.** Only essential fields appear during quick logging; contextual fields remain optional.
- **Progress should be explainable.** Every completed goal item can be traced to the experience that satisfied it.
- **Privacy is the default.** Viewing history, locations, companions, notes, watchlists, and goals are private unless explicitly shared in a future release.

## 3. MVP Scope

### Included

- Movies, TV shows, seasons, and episodes
- External title search and metadata
- Complete, partial, first-time, and repeat viewing experiences
- Optional location, companions, provider, edition, rating, reactions, and notes
- Movie and TV libraries
- Timeline and calendar history
- A lightweight watchlist
- Structured watching goals
- Active, paused, completed, and dropped goal views
- Whole-series, season, movie-list, and custom goals
- Automatic and manual experience-to-goal matching
- Watchlist-to-goal conversion
- Basic personal insights
- User authentication, data export, and account deletion

### Deferred

- Public profiles and social feeds
- Shared or competitive goals
- Recurring goals such as “one movie each week”
- Quantity challenges such as “watch 100 movies this year”
- Personalized recommendations
- Streaming playback or ticket purchasing
- Native mobile applications
- Other media types

The website should be responsive and installable as a Progressive Web App.

## 4. Domain Model

### 4.1 Media

Media describes the underlying work independently of any user. Media records form a shared catalog: one imported movie, show, season, or episode can be referenced by every user's experiences, watchlist entries, and goals.

```text
TV show
└── Season
    └── Episode

Movie
```

The catalog is populated on demand. When a user selects external search results, the application first looks for the provider ID locally. Existing records are reused; missing records are imported from the metadata provider. A unique constraint on provider and external ID prevents duplicate imports.

Shared metadata includes titles, descriptions, artwork, release dates, runtime, genres, languages, production countries, content ratings, creators, cast, and external provider IDs. Local IDs remain stable when imported metadata changes so personal records never depend directly on an external API object.

### 4.2 Release or edition

A release identifies the particular version watched when relevant, such as:

- Theatrical or director's cut
- Remaster or restoration
- Blu-ray, DVD, digital purchase, or streaming release
- Dubbed or subtitled presentation

Edition data is optional and should never block logging.

### 4.3 Media experience

A media experience records an actual viewing event. Examples include:

- Finishing a movie
- Watching part of a movie
- Watching one TV episode
- Rewatching an episode
- Watching the same title in a different context

Every experience belongs to a user and references a movie or episode. A media item may have any number of experiences.

An experience can exist without being on the watchlist or connected to a goal. Deleting or changing a goal must not delete or alter its experiences.

### 4.4 Watchlist entry

The watchlist is a low-commitment list of media a user may want to consume later.

A watchlist entry:

- Does not track completion progress
- Does not require start or target dates
- Can reference a movie, show, season, or episode
- Can be removed independently of viewing history
- Can be converted into a goal

Users may convert one TV show into a whole-series or selected-season goal, or combine several watchlist entries into a custom goal.

### 4.5 Watching goal

A watching goal defines a set of movies or episodes the user intends to complete.

Examples:

- Watch every episode of *Avatar: The Last Airbender*
- Finish Season 2 of a show
- Watch a film trilogy
- Watch a custom selection of horror movies
- Rewatch a series beginning on a specific date

A goal does not own experiences. It contains required goal items, and qualifying experiences provide evidence that those requirements were completed.

### 4.6 Goal item

A goal item is one required movie or episode. Selecting a show or season automatically expands it into episode-level items so progress and remaining work can be calculated accurately.

Repeatedly watching one episode creates multiple experiences but satisfies only one required item in a given goal.

### 4.7 Experience-goal match

A match associates an experience with a goal item. Matches may be:

- **Automatic:** Suggested or created because the media and completion rules match.
- **Manual:** Explicitly selected by the user.

Users can exclude an automatic match or add a missing one. One experience may count toward multiple goals.

## 5. Goal Rules and States

### 5.1 Goal lifecycle

Goals use a lifecycle status and, when applicable, an activity state.

```text
In progress
├── Actively watching
└── Paused

Completed

Dropped
```

Valid state combinations are:

- `IN_PROGRESS` + `ACTIVE`
- `IN_PROGRESS` + `PAUSED`
- `COMPLETED` with no activity state
- `DROPPED` with no activity state

The interface may present these simply as Active, Paused, Completed, and Dropped. Active goals receive the most prominence; paused goals are de-emphasized; completed and dropped goals are archived by default.

### 5.2 Experience eligibility

Each goal chooses one of two history rules:

- **All qualifying experiences:** Past and future experiences can satisfy requirements.
- **New experiences only:** Only experiences on or after the goal's start date qualify.

This distinction supports both lifetime completion tracking and intentional rewatches.

### 5.3 Goal scope

Series and season goals use one of two scope rules:

- **Snapshot:** Include episodes known when the goal is created.
- **Dynamic:** Automatically add newly released episodes.

Snapshot should be the default for the MVP. Dynamic scope is useful for currently airing shows.

Before creating a whole-series or season goal, the application should synchronize stale series metadata, import the selected seasons and episodes, and then create one goal item per selected episode. Specials and Season 0 are excluded by default but may be included manually.

When synchronization discovers a new episode, dynamic goals add a new goal item and recalculate progress. Snapshot goals remain unchanged but may offer the user an option to add the episode.

### 5.4 Progress calculation

Goal progress is based on unique completed goal items:

```text
completed goal items / total goal items × 100
```

A goal should display:

- Completed items
- Remaining items
- Percentage complete
- Estimated runtime remaining
- Last goal activity
- Progress by season, where relevant
- Suggested next item

A goal is automatically eligible to become Completed when every required item has a qualifying experience. The user should confirm completion so manual exceptions can be addressed.

## 6. Logging a Media Experience

### 6.1 Quick log

The default flow is:

1. Search for and select a movie, show, or episode.
2. For a show, select an episode or accept the suggested next episode.
3. Choose an action:
   - Watched
   - Watched part
   - Started
   - Finished
4. Confirm the date and time, defaulting to now.
5. Save.

### 6.2 Goal matching

If the selected media matches an active goal, the form displays an optional section:

```text
Counts toward
☑ Watch Avatar: The Last Airbender
☐ Favorite Animated Episodes
```

An obvious match may be preselected, but the user can remove it. Paused goals should not match automatically unless the user explicitly selects them.

After saving, the confirmation may show:

```text
Experience saved
Goal progress: 17 of 61 episodes · 28%
```

### 6.3 Optional experience details

An expandable **Add details** section includes:

- Start and end time
- Progress before and after the experience
- First watch or rewatch
- Location
- People watched with
- Streaming service, theater, broadcast, disc, or digital source
- Device
- Release, cut, language, subtitles, or dub
- Rating
- Reactions or mood tags
- Short review
- Private notes
- Favorite status

Dates may be exact or approximate so older memories can be logged without inventing precision.

### 6.4 Smart defaults

The application may suggest:

- Recent locations and companions
- Frequently used providers and devices
- The next episode of an active show or goal
- Previous progress for an unfinished movie
- Whether the experience is a rewatch
- Matching active goals

All inferred values must remain editable.

## 7. Main Interface

### 7.1 Navigation

Primary navigation should include:

- Home
- Library
- Timeline
- Watchlist
- Goals
- Insights

A persistent **Log experience** action should be available from every primary page.

### 7.2 Home dashboard

The dashboard prioritizes current activity:

- Log an experience
- Continue unfinished movies
- Active goals and their next suggested items
- Next episodes for active shows
- Recent experiences
- Watchlist preview
- Timeline preview
- A small monthly activity summary

Paused, completed, and dropped goals should not clutter the default dashboard.

### 7.3 Library

The Library contains Movies and TV Shows tabs with poster-grid and compact-list views.

Filters include:

- Ever watched or never watched
- First watch or rewatch
- Rating
- Genre
- Year watched or released
- Provider or format
- Location or companion
- On watchlist
- Included in an active goal

Sort options include recently experienced, title, release date, rating, watch count, and total viewing time.

### 7.4 Media detail pages

A movie page displays:

- Artwork and metadata
- Complete experience history
- Watch count and latest rating
- Versions previously watched
- Notes and reviews
- Watchlist and goal membership
- Actions to log an experience, add to watchlist, or add to a goal

A TV page additionally displays:

- Season and episode browser
- Historical per-episode completion indicators
- Latest episode experienced
- Next suggested episode
- Experiences grouped by season
- Goals containing the show or its episodes

The page should not rely on one global user-title status. Historical state is derived from experiences, while future intention is represented by the watchlist and goals.

### 7.5 Watchlist

The Watchlist supports:

- Movie and TV tabs
- Poster-grid and list views
- Date-added, priority, genre, and release-date sorting
- Multi-select
- Direct experience logging
- Removing entries
- Converting a show into a whole-series or selected-season goal
- Converting selected entries into a custom goal

Logging an experience can optionally remove the relevant item from the watchlist, based on user preference.

### 7.6 Goals

The Goals page provides filtered sections for:

- Active
- Paused
- Completed
- Dropped

Each card shows artwork, progress, completed and remaining counts, percentage, last activity, optional target date, and next suggested item.

A goal detail page includes:

- Goal name, description, artwork, and state
- Start and optional target dates
- Progress summary and remaining runtime
- Season breakdown when relevant
- Required media checklist
- Experiences satisfying each item
- Suggested next item
- Controls to edit, pause, resume, complete, drop, or restore the goal

### 7.7 Timeline

Experiences—not goals—are the primary timeline entries.

Each entry may show artwork, title or episode, date, completion state, rating, location, companions, and provider. If applicable, it can also show that the experience advanced a goal.

Timeline modes include:

- **Stream:** Cards grouped by day or month
- **Calendar:** Viewing activity density and daily details
- **Compact:** High-density long-term history

Users can filter by media type, date, rating, location, companion, provider, rewatch status, or associated goal. Consecutive episodes may collapse into a binge group.

### 7.8 Insights

Initial insights include:

- Movies and episodes watched
- Total estimated viewing time
- First watches versus rewatches
- Most-watched shows
- Most-used providers and locations
- Most-common viewing companions
- Monthly and yearly activity
- Goals completed
- Average goal completion time

Insights are calculated primarily from experiences, with separate goal-related statistics where appropriate.

## 8. Visual and Interaction Design

The application should feel cinematic and personal without resembling a streaming storefront.

- Dark theme as the initial direction, with an optional light theme
- Selective use of large artwork for recognition and atmosphere
- Neutral interface colors with one accent color
- Clear typography, strong contrast, and comfortable spacing
- Mobile-first logging and touch targets
- Subtle logging and progress animations
- Accessible keyboard navigation and screen-reader labels
- Reduced-motion support

Goal progress should use clear bars, counts, and checklists rather than excessive gamification. Timeline clarity takes priority over decorative animation.

## 9. Technical Architecture

### Application

- **Next.js and TypeScript**
- **React Server Components** with server actions or API routes where appropriate
- **Tailwind CSS**
- **Accessible headless UI primitives**, such as Radix UI
- Progressive Web App support

### Data and authentication

- **PostgreSQL**
- **Prisma ORM**
- **Auth.js** for email and supported OAuth authentication
- Object storage if user-uploaded attachments are added

### External metadata and shared catalog

Use TMDB initially for movie and TV search, artwork, credits, seasons, and episodes. Access it through a server-side metadata-provider service rather than calling it directly from interface components. This abstraction should expose application-level operations such as searching, importing a movie or series, and synchronizing a series so another provider can be added later.

The application imports media on demand instead of copying the full external catalog. The import flow is:

1. Search the external provider.
2. Check for an existing local record using provider and external ID.
3. Reuse the local record when found.
4. Otherwise import and upsert the title, seasons, and required episodes.
5. Return the stable local media ID to the rest of the application.

TMDB-derived metadata is shared globally, while experiences, watchlists, goals, locations, companions, ratings, and notes remain user-owned. Provider changes or outages must not delete or invalidate personal records.

### Metadata synchronization

Imported media stores `last_synced_at` and `next_sync_at`. TV series additionally store their release status, last known episode air date, and next known episode air date. The next air date helps schedule synchronization but is not the only refresh signal because schedules and metadata can change.

Use a hybrid synchronization policy:

- Refresh an actively airing series shortly after its next known episode air date.
- Refresh active series with no known next episode periodically.
- Refresh planned, in-production, recently released, and older media at intervals appropriate to how likely they are to change.
- Periodically compare TMDB's changed-title IDs with locally imported provider IDs and queue matching records for synchronization.
- Refresh infrequently changing media before the provider's maximum cache period expires.

Normal page access should use stale-while-revalidate behavior: return stored metadata immediately and enqueue a unique background synchronization job when it is stale. Operations that require an accurate episode set, especially creating a whole-series or season goal, should wait for stale metadata to synchronize first.

Synchronization jobs must be idempotent and protected by unique queue keys or locks so many users cannot trigger duplicate API work for the same title. Episodes and seasons are upserted by provider ID rather than deleted and recreated.

If an imported episode disappears from a later provider response, preserve its local record and all personal references. Mark it as missing or inactive at the provider instead of hard-deleting it. Dynamic goals may receive newly discovered episodes; snapshot goals never change automatically.

## 10. Database Model

### Core tables

- `users`
- `media_titles` — globally shared movies and TV shows
- `tv_seasons`
- `tv_episodes`
- `media_external_ids`
- `releases`
- `media_experiences`
- `watchlist_entries`
- `watching_goals`
- `watching_goal_items`
- `experience_goal_matches`
- `locations`
- `people`
- `media_experience_people`
- `providers`
- `reaction_tags`
- `media_experience_reactions`

### Important relationships

- A TV show has many seasons; a season has many episodes.
- Shared media records do not belong to an individual user.
- A movie or episode has many user-owned media experiences.
- An experience belongs to one user and references one stable local movie or episode ID.
- A user may have one watchlist entry per media item.
- A goal belongs to one user and has many goal items.
- A goal item references one required local movie or episode.
- An experience-goal match connects one experience to one goal item.
- An experience can match multiple goal items across different goals.
- A goal item may retain multiple related experiences but counts once toward progress.
- Locations, companion records, experiences, watchlists, and goals are private to their owner.

### Media catalog and synchronization fields

`media_titles`, `tv_seasons`, and `tv_episodes` use internal IDs for application relationships. External IDs are retained for importing, deduplication, and synchronization. The provider/external-ID pair must be unique for each entity type.

`media_titles` should include:

- `media_type`
- `title` and `original_title`
- Core descriptive and release metadata
- `release_status`
- `last_episode_air_at` for TV
- `next_episode_air_at` for TV
- `last_synced_at`
- `next_sync_at`
- `sync_state`
- `sync_error_count`
- `last_sync_error`
- `created_at`
- `updated_at`

`media_external_ids` should include:

- Local media ID
- Provider name
- External ID

Equivalent provider identifiers may initially be stored directly on season and episode records, with a separate mapping table added later if multiple providers are needed at those levels.

Imported records that disappear from provider responses should have fields such as `provider_visible`, `provider_last_seen_at`, or `metadata_status`. They must not be hard-deleted while personal data references them.

### Key goal fields

`watching_goals` should include:

- `user_id`
- `name`
- `description`
- `lifecycle_status`
- `activity_state`
- `experience_history_rule`
- `scope_rule`
- `start_date`
- `target_date`
- `completed_at`
- `dropped_at`
- `created_at`
- `updated_at`

Database validation should prevent invalid state combinations, such as a completed goal with an active activity state.

### Historical integrity

Progress before and after an experience should be stored on that experience. Goal-item matches should also be retained rather than inferred only at display time, allowing the user to inspect why a requirement is complete.

Recalculating a goal may suggest new matches, but it must not silently remove manual decisions. Metadata synchronization may update titles, artwork, air dates, runtimes, and episode information, but it must preserve internal media IDs and all user references.

Deleting or replacing provider-derived metadata must be treated separately from deleting personal data. If API access or licensing changes, experiences and goals remain intact even when some descriptive media fields or images must be removed.

## 11. Privacy and Data Ownership

- All user content is private by default.
- Location labels such as “Home” are sufficient; exact coordinates are never required.
- Companion records do not require those people to have accounts.
- Users can edit or delete any experience, watchlist entry, or goal.
- Deleting a goal removes its items and matches but preserves all experiences.
- Deleting an experience updates affected goal progress and clearly warns the user.
- Users can export experiences, watchlists, goals, and relevant metadata in common formats.
- Account deletion removes all private user data.

## 12. MVP Success Criteria

The first release is successful when a user can:

1. Create an account and search for movies, shows, seasons, and episodes.
2. Import missing media on demand and reuse existing shared media records without duplicate API calls.
3. Synchronize stale, actively releasing media without blocking normal browsing.
4. Create an episode-complete goal from a freshly synchronized series or season.
5. Log a complete or partial experience in less than 15 seconds.
6. Add optional context without slowing the default flow.
7. Record multiple experiences for the same media item.
8. Browse and filter their movie and TV history.
9. Explore experiences through a responsive timeline.
10. Add and remove simple watchlist entries.
11. Convert a show, season, or watchlist selection into a goal.
12. Create whole-series, season, movie-list, and custom goals.
13. Count either historical experiences or new experiences toward a goal.
14. Automatically and manually connect experiences to goal items.
15. View completed items, remaining items, percentage, and estimated remaining runtime.
16. Pause, resume, complete, drop, and restore goals.
17. Log experiences that are unrelated to any goal.
18. Edit or delete records while preserving clear historical and goal integrity.
19. Export personal viewing data.

The product should be judged primarily on three outcomes: logging remains effortless, viewing history feels meaningful, and goals provide useful structure without becoming mandatory.