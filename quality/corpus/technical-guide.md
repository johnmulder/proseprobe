# Configure retries

The client retries a failed request once after a 200 millisecond delay. It does
not retry authentication failures because another attempt cannot change the
credentials.

## Linux

Store the configuration in `/etc/example/client.toml`.

## macOS

Store the configuration in the application support directory.

## Windows

Store the configuration beside the user profile data.

| Setting | Default | Meaning |
| --- | ---: | --- |
| `attempts` | 2 | Total requests, including the first request |
| `delay_ms` | 200 | Delay before the retry |

Use [the retry reference](https://example.com/retries) for the complete option
list. The URL is documentation, not evidence that the client contacted a remote
service.

```python
client = Client(attempts=2, delay_ms=200)
```

The words speed, memory, and cost name three independent measurements in the
benchmark table; they are not a rhetorical list of benefits.

The first status message said the retry failed. The second stated that the retry
did not succeed.
