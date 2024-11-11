#include <iostream>
#include "srt_manager.h"

int main(int argc, char* argv[])
{
    printf("Hello World");
    SRTManager srt;
    srt.create_socket();
    srt.connect();
    srt.send_data();
}