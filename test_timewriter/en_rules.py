# -*- coding: utf-8 -*-
#
# Code released in the Public Domain. You can do whatever you want with this package.
# Look at README file to see how to adapt this program.
# Originally written by Pierre Métras <pierre@alterna.tv> for the OLPC XO laptop.
#######################################
# Timewriter rules for American English
#######################################

_time_rules = """
        time(12, 0) => noon |
        time(0, 0) => midnight |
        time(h, 0) => hour(h) o'clock am_pm(h) |
        time(h, m) [m < 10] => hour(h) o' min(m) am_pm(h) |
        time(h, m) [m >= 10] => hour(h) min(m) am_pm(h) |
        min(1) => one |
        min(2) => two |
        min(3) => three |
        min(4) => four|
        min(5) => five |
        min(6) => six |
        min(7) => seven |
        min(8) => eight |
        min(9) => nine |
        min(10) => ten |
        min(11) => eleven |
        min(12) => twelve |
        min(13) => thirteen |
	min(14) => fourteen |
        min(15) => fifteen |
        min(16) => sixteen |
        min(17) => seventeen |
        min(18) => eighteen |
        min(19) => nineteen |
        min(20) => twenty |
        min(21) => twenty-one |
        min(22) => twenty-two |
        min(23) => twenty-three |
        min(24) => twenty-four |
        min(25) => twenty-five |
        min(26) => twenty-six |
        min(27) => twenty-seven |
        min(28) => twenty-eight |
        min(29) => twenty-nine |
        min(30) => thirty |
        min(31) => thirty-one |
        min(32) => thirty-two |
        min(33) => thirty-three |
        min(34) => thirty-four |
        min(35) => thirty-five |
        min(36) => thirty-six |
        min(37) => thirty-seven |
        min(38) => thirty-eight |
        min(39) => thirty-nine |
        min(40) => fourty |
        min(41) => fourty-one |
        min(42) => fourty-two |
        min(43) => fourty-three |
        min(44) => fourty-four |
        min(45) => fourty-five |
        min(46) => fourty-six |
        min(47) => fourty-seven |
        min(48) => fourty-eight |
        min(49) => fourty-nine |
        min(50) => fifty |
        min(51) => fifty-one |
        min(52) => fifty-two |
        min(53) => fifty-three |
        min(54) => fifty-four |
        min(55) => fifty-five |
        min(56) => fifty-six |
        min(57) => fifty-seven |
        min(58) => fifty-eight |
        min(59) => fifty-nine |
        min(60) => sixty |
        hour(0) => twelve |
        hour(1) => one |
        hour(2) => two |
        hour(3) => three |
        hour(4) => four |
        hour(5) => five |
        hour(6) => six |
        hour(7) => seven |
        hour(8) => eight |
        hour(9) => nine |
        hour(10) => ten |
        hour(11) => eleven |
        hour(12) => twelve |
        hour(13) => one |
        hour(14) => two |
        hour(15) => three |
        hour(16) => four |
        hour(17) => five |
        hour(18) => six |
        hour(19) => seven |
        hour(20) => eight |
        hour(21) => nine |
        hour(22) => ten |
        hour(23) => eleven |
        am_pm(h) [ h < 12] => AM |
        am_pm(_) => PM 
    """
