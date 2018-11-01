# Useful snippets

## Database queries

### Query current states for all labels
```
SELECT history.label_name, history.created, history.new_state
FROM history
JOIN (
	SELECT label_name, MAX(created) AS max_created
	FROM history
	GROUP BY label_name
) latest_states
ON
	history.created = latest_states.max_created AND
	history.label_name = latest_states.label_name;
```

### Count number of labels in a specific state

```
SELECT COUNT(*)
FROM history
JOIN (
	SELECT label_name, MAX(created) AS max_created
	FROM history
	GROUP BY label_name
) latest_states
ON
	history.created = latest_states.max_created AND
	history.label_name = latest_states.label_name
WHERE history.new_state = 'STATE_NAME';
```
