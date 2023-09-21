# -*- coding: utf-8 -*-
from setuptools import setup

packages = \
['pyrate_limiter']

package_data = \
{'': ['*']}

extras_require = \
{'all': ['filelock>=3.0', 'redis>=3.3,<4.0', 'redis-py-cluster>=2.1.3,<3.0.0'],
 'docs': ['furo>=2022.3.4,<2023.0.0',
          'myst-parser>=0.17',
          'sphinx>=4.3.0,<5.0.0',
          'sphinx-autodoc-typehints>=1.17,<2.0',
          'sphinx-copybutton>=0.5',
          'sphinxcontrib-apidoc>=0.3,<0.4']}

setup_kwargs = {
    'name': 'pyrate-limiter',
    'version': '2.10.0',
    'description': 'Python Rate-Limiter using Leaky-Bucket Algorithm',
    'long_description': '<img align="left" width="95" height="120" src="docs/_static/logo.png">\n\n# PyrateLimiter\nThe request rate limiter using Leaky-bucket algorithm.\n\nFull project documentation can be found at [pyratelimiter.readthedocs.io](https://pyratelimiter.readthedocs.io).\n\n[![PyPI version](https://badge.fury.io/py/pyrate-limiter.svg)](https://badge.fury.io/py/pyrate-limiter)\n[![PyPI - Python Versions](https://img.shields.io/pypi/pyversions/pyrate-limiter)](https://pypi.org/project/pyrate-limiter)\n[![codecov](https://codecov.io/gh/vutran1710/PyrateLimiter/branch/master/graph/badge.svg?token=E0Q0YBSINS)](https://codecov.io/gh/vutran1710/PyrateLimiter)\n[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/vutran1710/PyrateLimiter/graphs/commit-activity)\n[![PyPI license](https://img.shields.io/pypi/l/ansicolortags.svg)](https://pypi.python.org/pypi/pyrate-limiter/)\n\n<br>\n\n## Contents\n- [PyrateLimiter](#pyratelimiter)\n  - [Contents](#contents)\n  - [Features](#features)\n  - [Installation](#installation)\n  - [Basic usage](#basic-usage)\n    - [Defining rate limits](#defining-rate-limits)\n    - [Applying rate limits](#applying-rate-limits)\n    - [Identities](#identities)\n  - [Handling exceeded limits](#handling-exceeded-limits)\n    - [Bucket analogy](#bucket-analogy)\n    - [Rate limit exceptions](#rate-limit-exceptions)\n    - [Rate limit delays](#rate-limit-delays)\n  - [Additional usage options](#additional-usage-options)\n    - [Decorator](#decorator)\n    - [Contextmanager](#contextmanager)\n    - [Async decorator/contextmanager](#async-decoratorcontextmanager)\n  - [Backends](#backends)\n    - [Memory](#memory)\n    - [SQLite](#sqlite)\n    - [Redis](#redis)\n    - [Custom backends](#custom-backends)\n  - [Additional features](#additional-features)\n    - [Time sources](#time-sources)\n  - [Examples](#examples)\n\n## Features\n* Tracks any number of rate limits and intervals you want to define\n* Independently tracks rate limits for multiple services or resources\n* Handles exceeded rate limits by either raising errors or adding delays\n* Several usage options including a normal function call, a decorator, or a contextmanager\n* Async support\n* Includes optional SQLite and Redis backends, which can be used to persist limit tracking across\n  multiple threads, processes, or application restarts\n\n## Installation\nInstall using pip:\n```\npip install pyrate-limiter\n```\n\nOr using conda:\n```\nconda install --channel conda-forge pyrate-limiter\n```\n\n## Basic usage\n\n### Defining rate limits\nConsider some public API (like LinkedIn, GitHub, etc.) that has rate limits like the following:\n```\n- 500 requests per hour\n- 1000 requests per day\n- 10000 requests per month\n```\n\nYou can define these rates using the `RequestRate` class, and add them to a `Limiter`:\n``` python\nfrom pyrate_limiter import Duration, RequestRate, Limiter\n\nhourly_rate = RequestRate(500, Duration.HOUR) # 500 requests per hour\ndaily_rate = RequestRate(1000, Duration.DAY) # 1000 requests per day\nmonthly_rate = RequestRate(10000, Duration.MONTH) # 10000 requests per month\n\nlimiter = Limiter(hourly_rate, daily_rate, monthly_rate)\n```\n\nor\n\n``` python\nfrom pyrate_limiter import Duration, RequestRate, Limiter\n\nrate_limits = (\n      RequestRate(500, Duration.HOUR), # 500 requests per hour\n      RequestRate(1000, Duration.DAY), # 1000 requests per day\n      RequestRate(10000, Duration.MONTH), # 10000 requests per month\n)\n\nlimiter = Limiter(*rate_limits)\n```\n\nNote that these rates need to be ordered by interval length; in other words, an hourly rate must\ncome before a daily rate, etc.\n\n### Applying rate limits\nThen, use `Limiter.try_acquire()` wherever you are making requests (or other rate-limited operations).\nThis will raise an exception if the rate limit is exceeded.\n\n```python\nimport requests\n\ndef request_function():\n    limiter.try_acquire(\'identity\')\n    requests.get(\'https://example.com\')\n\nwhile True:\n    request_function()\n```\n\nAlternatively, you can use `Limiter.ratelimit()` as a function decorator:\n```python\n@limiter.ratelimit(\'identity\')\ndef request_function():\n    requests.get(\'https://example.com\')\n```\nSee [Additional usage options](#additional-usage-options) below for more details.\n\n### Identities\nNote that both `try_acquire()` and `ratelimit()` take one or more `identity` arguments. Typically this is\nthe name of the service or resource that is being rate-limited. This allows you to track rate limits\nfor these resources independently. For example, if you have a service that is rate-limited by user:\n```python\ndef request_function(user_ids):\n    limiter.try_acquire(*user_ids)\n    for user_id in user_ids:\n        requests.get(f\'https://example.com?user_id={user_id}\')\n```\n\n## Handling exceeded limits\nWhen a rate limit is exceeded, you have two options: raise an exception, or add delays.\n\n### Bucket analogy\n<img height="300" align="right" src="https://upload.wikimedia.org/wikipedia/commons/c/c4/Leaky_bucket_analogy.JPG">\n\nAt this point it\'s useful to introduce the analogy of "buckets" used for rate-limiting. Here is a\nquick summary:\n\n* This library implements the [Leaky Bucket algorithm](https://en.wikipedia.org/wiki/Leaky_bucket).\n* It is named after the idea of representing some kind of fixed capacity -- like a network or service -- as a bucket.\n* The bucket "leaks" at a constant rate. For web services, this represents the **ideal or permitted request rate**.\n* The bucket is "filled" at an intermittent, unpredicatble rate, representing the **actual rate of requests**.\n* When the bucket is "full", it will overflow, representing **canceled or delayed requests**.\n\n### Rate limit exceptions\nBy default, a `BucketFullException` will be raised when a rate limit is exceeded.\nThe error contains a `meta_info` attribute with the following information:\n* `identity`: The identity it received\n* `rate`: The specific rate that has been exceeded\n* `remaining_time`: The remaining time until the next request can be sent\n\nHere\'s an example that will raise an exception on the 4th request:\n```python\nfrom pyrate_limiter import (Duration, RequestRate,\n                            Limiter, BucketFullException)\n\nrate = RequestRate(3, Duration.SECOND)\nlimiter = Limiter(rate)\n\nfor _ in range(4):\n    try:\n        limiter.try_acquire(\'vutran\')\n    except BucketFullException as err:\n        print(err)\n        # Output: Bucket for vutran with Rate 3/1 is already full\n        print(err.meta_info)\n        # Output: {\'identity\': \'vutran\', \'rate\': \'3/1\', \'remaining_time\': 2.9,\n        #          \'error\': \'Bucket for vutran with Rate 3/1 is already full\'}\n```\n\nThe rate part of the output is constructed as: `limit / interval`. On the above example, the limit\nis 3 and the interval is 1, hence the `Rate 3/1`.\n\n### Rate limit delays\nYou may want to simply slow down your requests to stay within the rate limits instead of canceling\nthem. In that case you can use the `delay` argument. Note that this is only available for\n`Limiter.ratelimit()`:\n```python\n@limiter.ratelimit(\'identity\', delay=True)\ndef my_function():\n    do_stuff()\n```\n\nIf you exceed a rate limit with a long interval (daily, monthly, etc.), you may not want to delay\nthat long. In this case, you can set a `max_delay` (in seconds) that you are willing to wait in\nbetween calls:\n```python\n@limiter.ratelimit(\'identity\', delay=True, max_delay=360)\ndef my_function():\n    do_stuff()\n```\nIn this case, calls may be delayed by at most 360 seconds to stay within the rate limits; any longer\nthan that, and a `BucketFullException` will be raised instead. Without specifying `max_delay`, calls\nwill be delayed as long as necessary.\n\n## Additional usage options\nBesides `Limiter.try_acquire()`, some additional usage options are available using `Limiter.ratelimit()`:\n### Decorator\n`Limiter.ratelimit()` can be used as a decorator:\n```python\n@limiter.ratelimit(\'identity\')\ndef my_function():\n    do_stuff()\n```\n\nAs with `Limiter.try_acquire()`, if calls to the wrapped function exceed the rate limits you\ndefined, a `BucketFullException` will be raised.\n\n### Contextmanager\n`Limiter.ratelimit()` also works as a contextmanager:\n\n```python\ndef my_function():\n    with limiter.ratelimit(\'identity\', delay=True):\n        do_stuff()\n```\n\n### Async decorator/contextmanager\n`Limiter.ratelimit()` also support async functions, either as a decorator or contextmanager:\n```python\n@limiter.ratelimit(\'identity\', delay=True)\nasync def my_function():\n    await do_stuff()\n\nasync def my_function():\n    async with limiter.ratelimit(\'identity\'):\n        await do_stuff()\n```\n\nWhen delays are enabled for an async function, `asyncio.sleep()` will be used instead of `time.sleep()`.\n\n## Backends\nA few different bucket backends are available, which can be selected using the `bucket_class`\nargument for `Limiter`. Any additional backend-specific arguments can be passed\nvia `bucket_kwargs`.\n\n### Memory\nThe default bucket is stored in memory, backed by a `queue.Queue`. A list implementation is also available:\n```python\nfrom pyrate_limiter import Limiter, MemoryListBucket\n\nlimiter = Limiter(bucket_class=MemoryListBucket)\n```\n\n### SQLite\nIf you need to persist the bucket state, a SQLite backend is available.\n\nBy default it will store the state in the system temp directory, and you can use\nthe `path` argument to use a different location:\n```python\nfrom pyrate_limiter import Limiter, SQLiteBucket\n\nlimiter = Limiter(bucket_class=SQLiteBucket)\n```\n\nBy default, the database will be stored in the system temp directory. You can specify a different\npath via `bucket_kwargs`:\n```python\nlimiter = Limiter(\n    bucket_class=SQLiteBucket,\n    bucket_kwargs={\'path\': \'/path/to/db.sqlite\'},\n)\n```\n\n#### Concurrency\nThis backend is thread-safe.\n\nIf you want to use SQLite with multiprocessing, some additional protections are needed. For\nthese cases, a separate `FileLockSQLiteBucket` class is available. This requires installing the\n[py-filelock](https://py-filelock.readthedocs.io) library.\n```python\nlimiter = Limiter(bucket_class=FileLockSQLiteBucket)\n```\n\n### Redis\nIf you have a larger, distributed application, Redis is an ideal backend. This\noption requires [redis-py](https://github.com/andymccurdy/redis-py).\n\nNote that this backend requires a `bucket_name` argument, which will be used as a prefix for the\nRedis keys created. This can be used to disambiguate between multiple services using the same Redis\ninstance with pyrate-limiter.\n\n**Important**: you might want to consider adding `expire_time` for each buckets. In a scenario where some `identity` produces a request rate that is too sparsed, it is a good practice to expire the bucket which holds such identity\'s info to save memory.\n\n```python\nfrom pyrate_limiter import Limiter, RedisBucket, Duration, RequestRate\n\nrates = [\n    RequestRate(5, 10 * Duration.SECOND),\n    RequestRate(8, 20 * Duration.SECOND),\n]\n\nlimiter = Limiter(\n    *rates\n    bucket_class=RedisBucket,\n    bucket_kwargs={\n        \'bucket_name\':\n        \'my_service\',\n        \'expire_time\': rates[-1].interval,\n    },\n)\n\n```\n\n#### Connection settings\nIf you need to pass additional connection settings, you can use the `redis_pool` bucket argument:\n```python\nfrom redis import ConnectionPool\n\nredis_pool = ConnectionPool(host=\'localhost\', port=6379, db=0)\n\nrate = RequestRate(5, 10 * Duration.SECOND)\n\nlimiter = Limiter(\n    rate,\n    bucket_class=RedisBucket,\n    bucket_kwargs={\'redis_pool\': redis_pool, \'bucket_name\': \'my_service\'},\n)\n```\n\n#### Redis clusters\nRedis clusters are also supported, which requires\n[redis-py-cluster](https://github.com/Grokzen/redis-py-cluster):\n```python\nfrom pyrate_limiter import Limiter, RedisClusterBucket\n\nlimiter = Limiter(bucket_class=RedisClusterBucket)\n```\n\n### Custom backends\nIf these don\'t suit your needs, you can also create your own bucket backend by extending `pyrate_limiter.bucket.AbstractBucket`.\n\n\n## Additional features\n\n### Time sources\nBy default, monotonic time is used, to ensure requests are always logged in the correct order.\n\nYou can specify a custom time source with the `time_function` argument. For example, you may want to\nuse the current UTC time for consistency across a distributed application using a Redis backend.\n```python\nfrom datetime import datetime\nfrom pyrate_limiter import Duration, Limiter, RequestRate\n\nrate = RequestRate(5, Duration.SECOND)\nlimiter_datetime = Limiter(rate, time_function=lambda: datetime.utcnow().timestamp())\n```\n\nOr simply use the basic `time.time()` function:\n```python\nfrom time import time\n\nrate = RequestRate(5, Duration.SECOND)\nlimiter_time = Limiter(rate, time_function=time)\n```\n\n## Examples\nTo prove that pyrate-limiter is working as expected, here is a complete example to demonstrate\nrate-limiting with delays:\n```python\nfrom time import perf_counter as time\nfrom pyrate_limiter import Duration, Limiter, RequestRate\n\nlimiter = Limiter(RequestRate(5, Duration.SECOND))\nn_requests = 27\n\n@limiter.ratelimit("test", delay=True)\ndef limited_function(start_time):\n    print(f"t + {(time() - start_time):.5f}")\n\nstart_time = time()\nfor _ in range(n_requests):\n    limited_function(start_time)\n\nprint(f"Ran {n_requests} requests in {time() - start_time:.5f} seconds")\n```\n\nAnd an equivalent example for async usage:\n```python\nimport asyncio\nfrom time import perf_counter as time\nfrom pyrate_limiter import Duration, Limiter, RequestRate\n\nlimiter = Limiter(RequestRate(5, Duration.SECOND))\nn_requests = 27\n\n@limiter.ratelimit("test", delay=True)\nasync def limited_function(start_time):\n    print(f"t + {(time() - start_time):.5f}")\n\nasync def test_ratelimit():\n    start_time = time()\n    tasks = [limited_function(start_time) for _ in range(n_requests)]\n    await asyncio.gather(*tasks)\n    print(f"Ran {n_requests} requests in {time() - start_time:.5f} seconds")\n\nasyncio.run(test_ratelimit())\n```\n',
    'author': 'vutr',
    'author_email': 'me@vutr.io',
    'maintainer': 'None',
    'maintainer_email': 'None',
    'url': 'https://github.com/vutran1710/PyrateLimiter',
    'packages': packages,
    'package_data': package_data,
    'extras_require': extras_require,
    'python_requires': '>=3.7,<4.0',
}


setup(**setup_kwargs)
