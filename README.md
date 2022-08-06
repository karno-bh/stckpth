# How to Run

*It is assumed that Python runs under Virtual Environment. It is also assumed POSIX with 'make'.*
*It is is not the case, look at the command in the Makefile*

Most of the required command are aggregated in Makefile with needed dependencies. The default goal will install all
requirements, run the tests, and run the application. App port is 8080. Thus, to run it:

```commandline
$ make
```


# Design Considerations

## General Notes

Since the requirement is to hold the data for very limited period of time, the persistence of data is not required.
Thus, all relevant events will be stored in memory. The meaning of relevant events is that events that are older than
last round hour will not be stored. For instance, if it is 10:32:15AM now then only events up to 09:00:00AM will be
stored. It will reduce the memory consumptions and out of memory in general. In addition, RAM storage will allow more
heavy load and quicker responses in general.

_NOTE_: persisting events will be an  issue if the server crashed in general because the statistics after restart will
not be correct. (Yes, it is possible to have multiple nodes pointing to the same DB, however, the reliability in general
will not increase because the DB may have failures as well. As much as it will be reliable as slower it will be. The
fantasy can grow up to RAFT Algorithm.)

## Technology Stack

As the data will be stored in memory it raises another questing of how to achieve this. It is possible to have in-memory
storages (there are tons of them). However, it will require more complex setup. Personally, I think, it is enough to
have simple hand-written storage for such kind of task.

The Python's server world, in general, is mostly driven by WSGI. However, the most WSGI implementations use
multiprocessing pool. Yes, this is more reliable (since, if one process crashed, say, with out-of-memory  others are not
affected). From the other hand, first, it requires more complex setup and data-sharing scheme. For having "simple
hand-written data storage" it will be required to have this storage in the same process. There are two options
remaining: either it will be a thread pool or async server. In my opinion, async Python server is a kind of overkill.
Yes, there are implementations of such as Tornado. But, to be honest, Tornado is not Express, and Python is not NodeJS
(**IMHO**:NodeJS is in heart async which makes it much easier to code such things there).
Thus, [CherryPy](https://docs.cherrypy.dev/) chosen.
It is both multithreaded server and app framework with most simple setup required.

## Storage Details

The storage itself is implemented as [SortedList](https://grantjenks.com/docs/sortedcontainers/).
It is not from batteries; however, this is required for this task because there is no guaranty that events will come
in some order. Thus, it makes difficult to find relevant entries, and most important to clean old entries in place.
Without going into deep details, it is a O(log(n)) random access structure. Thus, overhead of appending/deleting won't
be too scary.

The access to storage is synchronized explicitly.
[For the regular list it mostly won't be needed because of GIL](https://docs.python.org/3/faq/library.html#what-kinds-of-global-value-mutation-are-thread-safe).
However, it is compound non-concurrent data structure thus required explicit synchronization. Though, CPython itself
is too much synchronized in particular.

Storage knows to clean itself with old data (as a consequence, not to accept). This is performed on accepting a new
event. *If after accepting an event there are events that are older than before last round hour they are cleaned.*

In addition, the app is decoupled from storage. If it will be required to change the storage it may be achieved by
providing a different storage. As well, it makes the app cleaner from concern separation view.

## Documentation/Tests/Etc.

Since it is not pretend to be a library there is no in-code documentation. The code with some belief is written in
self-documented manner.

Tests do not test inner components, but they directly send requests and get responses. This is to avoid tests
redundancy. If something is wrong in the inner components the tests upper tests will fail too.
