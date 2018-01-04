# Routemaster

[![CircleCI](https://circleci.com/gh/thread/routemaster.svg?style=shield&circle-token=3973777302b4f7f00f5b9eb1c07e3c681ea94f35)](https://circleci.com/gh/thread/routemaster) [![Coverage Status](https://coveralls.io/repos/github/thread/routemaster/badge.svg?branch=master)](https://coveralls.io/github/thread/routemaster?branch=master)

State machines as a service.

(The _master_ of _routes_ through a state machine.)

Routemaster targets Python 3.6 and above.


##### Useful Links

 - [Glossary](docs/glossary.md)
 - [Development Setup](docs/getting_started.md)


Please note, the below is currently intended to get everyone on the same page
about what Routemaster is, rather than as a list of current features. When we
publish Routemaster this may form the basis of a blog post, or the introduction
to the documentation.


## Motivation for Routemaster

Routemaster was born at [Thread](https://www.thread.com/) out of the need for a
complex state machine for our email drip-feed system.

The drip feed had to be able to integrate data entered by users, recommendations
created by our recommendations service, realtime insights generated by our
realtime data pipeline (Bazalgette) and A/B tests being run by our split testing
system ([Jacquard](https://github.com/prophile/jacquard)).

We also came to build Routemaster as a replacement for a third party service
that was a poor fit for us given our significant complexity and data consistency
requirements, and that created significant operational complexity in
understanding the system when it went wrong.

With all of these separate services needing to integrate with the drip feed, a
backlog of ideas to test in the drip feed, and the need for a system that we
could understand at a level above our previous implementation, we decided to
build a generic state machine service that would be able to scale to our future
requirements.


## Design

Routemaster is designed to be understandable. At any given time, the location of
a [label][label], the reason for it not progressing to the next state, its
current planned route through the state machine, and the whole shape of the
state machine, should be easy to inspect, and easy to understand.

As a result, no external system is able to directly change the state of a label
in a state machine. The most an external client can do is push more
[metadata][metadata] into the system that _may_ change the state of a label,
depending on how the state machine is configured.

Routemaster is also designed to operate in a multi-service environment, where
multiple systems may want to affect the route of a label through a state
machine. This is where the benefits of not allowing clients to explicitly move a
label pay off.


### State machines

A state machine is a series of states, with defined transitions between states,
and conditions for when those transitions are allowed to occur.

A single Routemaster instance can manage multiple state machines.


### Labels

Labels are the core element that moves through a state machine. A label is
simply a string. It is assumed that clients to Routemaster will use labels that
make sense for their use-cases, such as database primary keys, UUIDs, etc.
Routemaster treats the label as opaque data and imparts no semantics onto it.

Given that a label is the only piece of data required for a state machine to
work, it follows that labels must be unique within a state machine. However
there are no such requirements between multiple state machines—in fact
internally the primary key on the labels table is composed of the label name
and the state machine's name.


### States

States in a state machine can either be an [_action_][action] or a
[_gate_][gate].


#### Actions

An action has an associated URL that is called on entry into the state, in order
for an external system to perform the action associated with that state.
Routemaster will keep re-trying requests to the URL until it receives a 200
series status code, or until a certain number of attempts have been made. At
this point the label will be marked as "errored" and no longer retried.

Requests are made as HTTP `POST` requests with the label metadata included as
JSON encoded body data.

Once a successful request has been made the label moves out of the action state
and directly into the next state.


#### Gates

A gate is a state that that may prevent a label from progressing until an [exit
condition][exit-condition] is met. Routemaster will evaluate the exit condition
in response to configurable triggers, and advance any label that passes the
condition.


##### Exit conditions

Exit conditions are small programs which execute with a [context][context]
formed of the metadata attached to a label, optional dynamic data fetched from
data feeds, and system provided data including the current date and time, and
the time that has passed since the label entered the current state.

All exit conditions evaluate to a either a truthy value, in which case the label
progresses to the next state, or to a falsy value, in which the label remains at
the gate.

An example of an exit condition is:

```
metadata.has_recommendations and
12h has passed since system.entered_state and
system.time >= 18:30
```

This will prevent the label (in this example a user) from progressing until
another system has pushed `{"has_recommendations": true}` into the metadata, and
the label has been in this state for at least 12 hours (in this case so we space
emails apart far enough), and the time is after 18:30, as we know that is a time
when emails have a good impact.

This exit condition does not itself mean that the next state, an action to send
an email, will be performed at 18:30, for that we will need the correct trigger
configuration.


##### Triggers

Triggers define when an exit condition will be evaluated, and the label moved to
the next state if necessary.

There are 3 types of trigger:

 - **Metadata** — triggers whenever the metadata for a label is updated at a given path.
 - **Time** — triggers each day at the given time.
 - **Interval** — triggers every given interval (i.e. 1 hour, 5 minutes)


### Data feeds

In some cases it might not be easy or appropriate to _push_ data into
Routemaster, so Routemaster is also able to _pull_ data in from external
sources.

Data feeds are defined at the state machine level, and are formed of a pair of a
name and a URL. The string `<label>` in the URL will be replaced with the
correct label when requested. For example:

```yaml
feeds:
  - name: split_tests
    url: http://localhost:8001/user/<label>
```

When evaluating the any exit condition in the state machine that uses any value
below the path `feeds.split_tests`, for the user with the label `88625`,
Routemaster will issue an HTTP `GET` to the URL
`http://localhost:8001/user/88625`, accepting a JSON encoded response and
providing it in the exit condition context at the path `feeds.split_tests`.

_Note that because feed data is pulled in, it cannot be used in metadata
triggers, in fact Routemaster refers to feed data and metadata separately in
order to make this distinction as clear as possible._


### Transitions

Transitions from a state to the next state(s) are defined in `next` blocks in
the config file. There are two types of transition:

**Constant transitions** are exactly what they sound like, they always
transition a label to the same next state.

**Context transitions** use the value at a path in the label's context to
determine the destination. This is the same context as used in the exit
condition evaluation that will have taken place immediately beforehand.

These transitions map a set of possible values at the path in the context to a
set of state names. Multiple values may map to the same next state, but the same
value cannot map to multiple states. A default state must also be provided for
cases where the value does not match any of the given options.

_Note that it is left up to the person configuring the state machine to
exhaustively cover all the possible values for the key at the given path if they
wish to do so. Since these values could come from data feeds at evaluation time,
no validation for exhaustiveness is done._

There is also an implicit third type of transition, the null transition, which
results from not specifying any other transition. This creates an end state that
cannot be progressed from.


[label]: docs/glossary.md#label
[metadata]: docs/glossary.md#metadata
[action]: docs/glossary.md#action
[gate]: docs/glossary.md#gate
[exit-condition]: docs/glossary.md#exit-condition
