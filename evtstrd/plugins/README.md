# Plugin directory

Plugins can be dropped into this directory to extends the functionality
of eventstreamd. Each plugin must have a fixed name, depending on
its functionality. Multiple plugins with the same functionality
are not supported.

For each plugin type there is an example plugin named `example_<type>.py`.

The following plugin types are supported:

## `auth.py` - Authorization Handling

`auth.py` must contain an async function with the following signature:

```python
async def check_auth(route, headers, **kwargs): ...
```

* `route` is either `"events"` or `"stats"`.
* `headers` is a mapping between header names (in lower-case) and
  their respective values. Treat this mapping as immutable.
* `**kwargs` are additional arguments, depending on the route.
  For future compatibility, `check_auth()` is expected to accept
  any argument, even if it is not listed here. Currently the following
  extra argument is supplied for the `"events"` route:
    * `subsystem`
* The return value must be mapping with the following fields:
    * `status` (required) - Either of `"ok"`, `"unauthorized"`, or `"forbidden"`.
    * `authenticate` (required if status is `"unauthorized"`) - content
      of the `WWW-Authenticate` header returned to the client
    * `expire` (optional) - If status is `"ok"` and this is not `None`,
      will send a `logout` event when this time is reached. Must be
      a `datetime` object without timezone or timezone set to UTC.

  Unknown fields are ignored.
