def test_login():
    # 模拟一个失败测试：期待 login() 返回 True
    from src.auth.login import login
    assert login("alice", "pw") is True
