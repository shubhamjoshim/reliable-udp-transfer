cmake_minimum_required(VERSION 3.16)

project(SDN_File_Transfer C)

set(CMAKE_C_STANDARD 11)

add_executable(sender sender.c)
add_executable(receiver receiver.c)
