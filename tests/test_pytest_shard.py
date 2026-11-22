from scripts.pytest_shard import shard_items


def test_shards_partition_collection_and_keep_execution_order() -> None:
    items = ['z', 'd', 'a', 'c', 'b', 'e', 'f']
    shards = [shard_items(items, index, 3, key=str) for index in range(3)]
    assert shards == [
        ['z', 'd', 'a'], ['b', 'e'], ['c', 'f']
    ]
    assert sorted(item for shard in shards for item in shard) == sorted(items)


def test_single_shard_keeps_original_collection() -> None:
    assert shard_items(['b', 'a'], 0, 1, key=str) == ['b', 'a']
