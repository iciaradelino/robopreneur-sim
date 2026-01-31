# sampling functions for the config
import numpy as np

def sample_reward(reward_config, rng):
    """sample reward from lognormal distribution"""
    median = reward_config['median']
    sigma_g = reward_config['sigma_g']
    
    if sigma_g == 0:
        return median  # deterministic
    
    # lognormal parameters: mu = ln(median), sigma = sigma_g
    mu = np.log(median)
    return rng.lognormal(mu, sigma_g)

def sample_work_time(time_config, rng):
    """sample work time from normal distribution with minimum"""
    mean = time_config['mean']
    sd = time_config['sd']
    min_time = time_config['min']
    
    if sd == 0:
        return mean  # deterministic
    
    # sample from normal and apply minimum
    sampled_time = rng.normal(mean, sd)
    return max(sampled_time, min_time)