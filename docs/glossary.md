# Glossary

|Term|Definition|
|---|---|
|routemaster|A state machine service|
|label|A single named entity moving through a single state machine. Note the primary key is `(state_machine, label)`, i.e. labels have no meaning between separate state machines.|
|metadata|Arbitrary metadata associated with a label, used to decide how that label should progress through a state machine. The exit condition DSL can access this through the `metadata` prefix.|
|feed|A dynamic data source, retrieved lazily, and accessible through the `feed` prefix.|
|system|The prefix for injected constants in the exit condition DSL.|
|context|The context in which exit condition programs run.|
|state|A single node in the state machine.|
|action|A type of state that triggers a side-effect in an external service upon a label entering it. A label remaining here implies that routemaster has been unable to successfully trigger the side-effect.|
|gate|A type of state that restricts a label from continuing, based on an **exit condition**.|
|exit condition|A conditional statement that resolves to either true or false, deciding whether a label can leave the associated state. Can be dependent on the **context**, external data feeds, the current time, or the duration that a label has been in the state|
