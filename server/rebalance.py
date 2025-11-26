from server.encoding_transformer_utils import path_to_OPC, string_to_binary_data
from server.encoding_transformer_utils import get_table_name

class CBT_node: # complete binary tree
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None


class AVL_Node:
    def __init__(self, v, path=None):
        self.value = v
        self.left = None
        self.right = None
        self.parent = None
        self.path = path
        self.ids = []  # 存储数据库中具有相同值的不同 ID

    # __repr__ 用于调试打印
    def __repr__(self):
        # 为了避免无限递归，打印节点的关键信息
        left_value = self.left.value if self.left else None
        right_value = self.right.value if self.right else None
        parent_value = self.parent.value if self.parent else None

        return f"AVL_Node(value={self.value}, " \
               f"left={left_value}, right={right_value}, " \
               f"parent={parent_value}, path={self.path})" \


def subtree_size(node):
    if node is None:
        return 0
    if node.left is None and node.right is None:
        return 1
    elif node.left is None:
        return 1 + subtree_size(node.right)
    elif node.right is None:
        return 1 + subtree_size(node.left)
    else:
        return 1 + subtree_size(node.left) + subtree_size(node.right)

def counter(fn):
    def wrapper(*args, **kwargs):
        node = args[0]
        wrapper.subtree_size = subtree_size(node)
        # wrapper.subtree_sizes += [subtree_size(node)]
        return fn(*args, **kwargs)
    wrapper.subtree_sizes = []
    wrapper.__name__ = fn.__name__
    return wrapper

def height(node):
    if node is None:
        return 0
    if node.left is None and node.right is None:
        return 1
    elif node.left is None:
        return 1 + height(node.right)
    elif node.right is None:
        return 1 + height(node.left)
    else:
        return 1 + max(height(node.left), height(node.right))


def balance_factor(node):
    return height(node.left) - height(node.right)


def update_paths(node, path, db_manager, logger): # 更新以node为根的子树的path
    if node is None:
        return

    if node.path != path:
        node.path = path

    # 同步调整数据库中的编码值
    OPC = path_to_OPC(path)
    update_query = f"UPDATE {get_table_name()} SET OPC = %s WHERE insert_num = %s"
    update_params = [(string_to_binary_data(OPC), node.value)]
    db_manager.execute_update(update_query, update_params)  # 数据插入到数据库中

    if node.left:
        update_paths(node.left, path + "0", db_manager, logger)
    if node.right:
        update_paths(node.right, path + "1", db_manager, logger)


def _create_complete_binary_tree(N):
    if N < 1:
        return None
    node_num = 2 * N + 5
    nodes = [CBT_node(i) for i in range(1, node_num + 1)]

    for i in range(node_num):
        left_child_index = 2 * i + 1
        right_child_index = 2 * i + 2
        if left_child_index < node_num:
            nodes[i].left = nodes[left_child_index]
        if right_child_index < node_num:
            nodes[i].right = nodes[right_child_index]

    return nodes

def collect_unbalanced_nodes(node, logger, N):
    '''收集失衡节点，返回节点数组list'''
    list = [None] * (2*N+6)
    list[1] = node
    cur_node = node

    for i in range(1, N+2): # range左闭右开
        # 更深节点做主干节点，更浅节点做从属节点
        left_height = height(cur_node.left)
        right_height = height(cur_node.right)

        if left_height == 0:
            left_node = AVL_Node(list.index(cur_node)+N+3, cur_node.path + '0')
            cur_node.left = left_node
            left_node.parent = cur_node
        elif right_height == 0:
            right_node = AVL_Node(list.index(cur_node)+N+3, cur_node.path + '1')
            cur_node.right = right_node
            right_node.parent = cur_node

        if left_height > right_height:
            list[i+1] = cur_node.left
            list[i+N+3] = cur_node.right
            cur_node = cur_node.left
        else:
            list[i+1] = cur_node.right
            list[i+N+3] = cur_node.left
            cur_node = cur_node.right

    if list[N+2].left == None:
        left_node = AVL_Node(N+3, list[N + 2].path + '0')
        list[N + 2].left = left_node
        left_node.parent = list[N+2]
    if list[N+2].right == None:
        right_node = AVL_Node(2*N+5, list[N + 2].path + '1')
        list[N + 2].right = right_node
        right_node.parent = list[N+2]

    list[N+3] = list[N+2].left
    list[2*N+5] = list[N+2].right

    return list


def LDR(cur_node, list, arr, logger):
    '''中序遍历失衡子树，生成中序遍历节点编号数组arr'''
    if cur_node is None:
        return

    LDR(cur_node.left, list, arr, logger)
    logger.debug(f"cur_node={cur_node}")
    if cur_node in list:
        arr.append(list.index(cur_node))
    else:
        return
    LDR(cur_node.right, list, arr, logger)


def ordered_complete_binary_tree(N, logger):
    '''构建有序完全二叉树，数组arr2'''
    nodes = _create_complete_binary_tree(N)
    nodes.insert(0, CBT_node(0))
    root_node = nodes[1]
    arr2 = []
    LDR(root_node, nodes, arr2, logger)
    return arr2


def reordering_complete_binary_tree(N, arr1, arr2, list, logger):
    '''重排序完全二叉树'''
    # logger.info(f"arr1={arr1}, arr2={arr2}, list={list}") # 正常

    node_num = 2 * N + 5
    index = [None] * (node_num + 1)
    for i in range(node_num):
        index[arr2[i]] = arr1[i]

    index = index[1:]
    # logger.info(f'index[]= {index}')

    root_node = list[index[0]]

    for i in range(node_num):
        left_child_index = 2 * i + 1 # index数组下标
        right_child_index = 2 * i + 2

        cur_node = list[index[i]]

        if left_child_index < node_num and list[index[left_child_index]].value not in range(2*N+6): # 左孩子存在且非虚拟节点
            cur_node.left = list[index[left_child_index]]
            list[index[left_child_index]].parent = cur_node
        elif left_child_index < node_num and list[index[left_child_index]].value in range(2*N+6):
            cur_node.left = None

        if right_child_index < node_num and list[index[right_child_index]].value not in range(2*N+6): # 右孩子存在且非虚拟节点
            cur_node.right = list[index[right_child_index]]
            list[index[right_child_index]].parent = cur_node
        elif right_child_index < node_num and list[index[right_child_index]].value in range(2*N+6):
            cur_node.right = None

    return root_node


def print_tree(root, logger):
    if root is None:
        return
    logger.info(f'{root}')         # 先打印当前节点
    print_tree(root.left, logger)     # 再打印左子树
    print_tree(root.right, logger)    # 最后打印右子树


@counter
def rebalance(node, db_manager, logger, N):
    if abs(balance_factor(node)) > N:
        path = node.path
        parent = node.parent

        unbalanced_nodes_list = collect_unbalanced_nodes(node, logger, N)

        arr1 = []

        LDR(node, unbalanced_nodes_list, arr1, logger)

        arr2 = ordered_complete_binary_tree(N, logger)

        # arr1和arr2都是大小为2N+5的数组
        new_root_node = reordering_complete_binary_tree(N, arr1, arr2, unbalanced_nodes_list, logger)

        update_paths(new_root_node, path, db_manager, logger)

        if parent is not None:
            new_root_node.parent = parent
            if path[-1] == '0':
                parent.left = new_root_node
            else:
                parent.right = new_root_node
        else:
            new_root_node.parent = None

        return new_root_node

    else:
        return node