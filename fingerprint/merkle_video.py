from crypto.sm3_hash import str_sm3

def build_merkle_root(hash_list: list[str]) -> str:
    nodes = hash_list.copy()
    while len(nodes) > 1:
        new_nodes = []
        for i in range(0, len(nodes), 2):
            a = nodes[i]
            b = nodes[i+1] if i+1 < len(nodes) else a
            combined = a + b
            new_nodes.append(str_sm3(combined))
        nodes = new_nodes
    return nodes[0] if nodes else ""
