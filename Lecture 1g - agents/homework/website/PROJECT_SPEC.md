# Personal Movie & TV Tracker — Product Specification

## 1. Product Summary

A private-first personal media journal for recording movies and TV episodes as lived experiences—not just titles on a checklist.

Users can quickly log what they watched, then optionally add context such as where they watched it, who they watched with, the service or physical copy used, their reaction, and whether they finished it. Over time, these entries create a searchable library and a visual timeline of the user's viewing history.

**Product promise:** Logging should take only a few seconds, while still supporting rich detail for users who want it.

## 2. Goals

- Make logging a movie or TV episode possible in under 15 seconds.
- Preserve the context around each viewing without requiring every field.
- Clearly distinguish a title from an individual viewing of that title.
- Support rewatches and repeated episode viewings naturally.
- Give users two useful ways to revisit their history:
  - A browsable media library
  - A chronological, visually rich timeline
- Keep viewing history private by default.

## 3. Scope

### Included in the first release

- Movies
- TV shows, seasons, and episodes
- Title search and metadata
- Quick and detailed logging
- Partial watches and completed watches
- Rewatches
- Ratings, reactions, and notes
- Locations and viewing companions
- Streaming, theater, broadcast, digital, and physical formats
- Movie and TV library pages
- Timeline and calendar views
- Basic statistics and filters
- User authentication and account settings

### Not included initially

- Public social feeds, followers, likes, or comments
- Personalized content recommendations
- Ticket purchasing or streaming playback
- Books, games, music, podcasts, or other media types
- Advanced AI-generated analysis
- Native mobile applications

The website should be responsive and installable as a Progressive Web App so it works well on phones before native applications are considered.

## 4. Core Concepts

### Title

The underlying movie or TV show. Examples include *Arrival* or *Severance*. Metadata such as artwork, cast, release year, runtime, and genres belongs to the title.

### Episode

A specific episode belonging to a TV season and show. An episode can be logged independently and inherits information from its parent show.

### Release or edition

The particular version watched, when relevant. Examples include a theatrical cut, director's cut, remaster, Blu-ray release, digital purchase, or dubbed version.

### Viewing session

A record of an actual viewing experience. It contains the date, progress, location, companions, platform, rating, and notes. One title can have many viewing sessions.

### User-title state

The user's overall relationship with a title:

- Want to watch
- Watching
- Completed
- Paused
- Abandoned

This state is calculated from viewing history when possible but may be manually changed.

## 5. Logging Experience

### Quick log

The default flow should request only:

1. Search for and select a movie, show, or episode.
2. Choose the viewing action:
   - Watched
   - Watched part of it
   - Started
   - Finished
3. Confirm the date and time, defaulting to now.
4. Save.

For a TV show, search results should make it easy to select the next unwatched episode. After logging an episode, the app should suggest the following episode.

### Optional details

An expandable **Add details** section may include:

- Start and end time
- Progress before and after the session
- First watch or rewatch
- Location
- People watched with
- Viewing method or provider
- Release, cut, language, subtitles, or dub
- Rating
- Reactions or mood tags
- Short review
- Private notes
- Favorite status

None of these fields should block saving.

### Smart defaults

The app should reduce repeated work by suggesting:

- The user's recent location
- Frequently selected companions
- Common streaming services or devices
- The next episode of an active show
- The last recorded progress for an unfinished movie
- Whether a session is likely a rewatch

Users must be able to edit all inferred values.

## 6. Information to Track

### Shared movie and TV metadata

- Title
- Original title
- Description
- Poster and backdrop images
- Release date or first-air date
- Runtime
- Genres
- Original language
- Production countries
- Creators, directors, cast, and crew
- Content rating
- External metadata provider ID

### TV-specific metadata

- Show status
- Season number
- Episode number
- Episode title and description
- Episode air date and runtime
- Season and series artwork

### Viewing-session data

- User
- Movie or episode watched
- Date and optional start/end time
- Time-zone offset
- Progress before and after viewing
- Completion state
- First watch or rewatch
- Location
- Companions
- Viewing method and provider
- Edition or version
- Audio language and subtitle language
- Rating
- Reaction tags
- Review and private notes
- Favorite status
- Created and last-updated timestamps

Dates may be exact or approximate so users can add older memories such as “Summer 2022” without inventing a precise date.

## 7. Main Interface

### Home dashboard

The dashboard should prioritize action and recent activity:

- Prominent **Log a viewing** button
- Continue-watching section
- Next episodes for active shows
- Recently watched titles
- A small timeline preview
- Lightweight insights such as this month's viewing count

### Search and quick-log overlay

Search should open quickly from anywhere. Results should be grouped into movies, shows, and episodes. Selecting a result opens a compact logging form rather than forcing navigation to another page.

### Library

The library contains separate **Movies** and **TV Shows** tabs.

Users can switch between poster grid and compact list views and can filter by:

- Status
- Watched or unwatched
- First watch or rewatch
- Rating
- Genre
- Year watched
- Release year
- Provider or format
- Location
- Companion

Sorting options include recently watched, title, release date, rating, total watch count, and total time watched.

### Media detail page

A movie page should show:

- Artwork and metadata
- Current user status
- Average or latest personal rating
- Watch count
- All viewing sessions in chronological order
- Versions or editions previously watched
- Notes and reviews
- A quick rewatch button

A TV page should additionally show:

- Season and episode browser
- Per-episode completion indicators
- Overall series progress
- Next unwatched episode
- Viewing history grouped by season

### Timeline

The timeline is the app's signature history view. It should combine strong visuals with efficient scanning.

Each timeline entry displays recognizable artwork, title or episode, date, completion state, rating, location, companions, and provider when available.

Timeline modes:

- **Stream:** Chronological viewing cards grouped by day or month
- **Calendar:** Activity density with daily details
- **Compact:** High-density history for long-term users

Users can filter the timeline by media type, date range, rating, location, companion, provider, and first-watch/rewatch status. Multiple episodes watched consecutively should optionally collapse into a single binge group.

### Insights

The initial insights page should remain useful but modest:

- Movies watched
- Episodes watched
- Total estimated viewing time
- First watches versus rewatches
- Most-watched shows
- Most-used providers and locations
- Most-common viewing companions
- Monthly and yearly activity

Statistics should be calculated from viewing sessions, not merely library status.

## 8. Visual Design Direction

The experience should feel cinematic and personal without resembling a streaming-service storefront.

- Dark theme as the primary visual direction, with an optional light theme
- Large artwork used selectively for recognition and atmosphere
- Neutral interface colors with one configurable accent color
- Distinct but restrained movie and TV indicators
- Clear typography and high contrast
- Subtle transitions for timeline expansion and logging confirmation
- Mobile-first quick logging with comfortable touch targets
- Accessible keyboard navigation, focus states, and screen-reader labels

The timeline should favor clarity over decorative animation. Motion must respect reduced-motion preferences.

## 9. Suggested Technical Architecture

### Frontend and application layer

- **Next.js with TypeScript** for the responsive web application
- **React Server Components and server actions/API routes** where appropriate
- **Tailwind CSS** for the design system and responsive styling
- **Accessible headless components** such as Radix UI primitives

### Data and authentication

- **PostgreSQL** as the primary relational database
- **Prisma ORM** for schema management, migrations, and type-safe queries
- **Auth.js** for email and supported OAuth authentication
- Object storage for user-uploaded avatars or viewing photos if attachments are added

### External metadata

Use a dedicated movie/TV metadata provider for title search, artwork, cast, seasons, and episodes. Store provider IDs and cache the metadata needed by the interface. User-created viewing records must remain independent from the provider so they are not lost if metadata changes.

## 10. Database Model

A practical initial relational model includes:

- `users`
- `media_titles` — shared movie and TV metadata
- `tv_seasons`
- `tv_episodes`
- `releases` — cuts, physical editions, or other versions
- `viewing_sessions`
- `locations`
- `people` — private companion records owned by a user
- `viewing_session_people` — many-to-many session companions
- `providers` — streaming service, theater, broadcast, disc, or digital source
- `reaction_tags`
- `viewing_session_reactions`
- `user_title_states`

Important relationships:

- A TV title has many seasons; a season has many episodes.
- A title or episode has many viewing sessions.
- A viewing session belongs to one user and references either a movie or episode.
- A session may reference one release, provider, and location.
- A session may have multiple companions and reactions.
- Locations and companion records are private to their owner.

Progress should be stored explicitly on each session so edits to later sessions do not erase historical state.

## 11. Privacy and Data Ownership

- All accounts and entries are private by default.
- Exact locations should never be requested automatically without clear consent.
- A location may be a simple label such as “Home” rather than GPS coordinates.
- Companion records should not require those people to have accounts.
- Users should be able to export their history in a common format.
- Account deletion should remove personal viewing data and private companion/location records.

## 12. MVP Success Criteria

The first release is successful when a user can:

1. Create an account.
2. Search for a movie, show, or episode.
3. Log a completed or partial viewing in under 15 seconds.
4. Add optional context without cluttering the basic flow.
5. Record multiple viewings of the same title.
6. Track episode-level TV progress.
7. Browse and filter their movie and TV libraries.
8. Explore their complete history in a responsive timeline.
9. Edit or delete any viewing session.
10. Export their viewing records.

The product should be judged primarily on the speed of logging and the usefulness of the history it creates—not on the total number of available fields.