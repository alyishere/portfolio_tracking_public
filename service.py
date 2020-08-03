def report():
    import caching
    import gain_loss_calculation
    import RBHD
    monthly_return = RBHD.monthly_return_RBHD()
    print(monthly_return)
report()
